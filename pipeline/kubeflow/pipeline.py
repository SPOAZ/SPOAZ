from kfp.v2.dsl import component, Output, Input, Dataset, Model, pipeline
from google.cloud import bigquery
from kfp.v2 import compiler
import google.cloud.aiplatform as aip

@component(packages_to_install=["google-cloud-bigquery", "pandas"],base_image='asia-northeast3-docker.pkg.dev/GCP_PROJECT_NAME/pipeline/dataextract:1')
def extract_playlists_to_gcs(project_id: str, dataset_id: str, table_id: str, exclude_field: str, gcs_output_path: str, output_csv: Output[Dataset]):
    from google.cloud import bigquery
    
    def create_query_exclude_field(dataset_id, table_id, exclude_field, client):
        table_ref = f"{client.project}.{dataset_id}.{table_id}"
        table = client.get_table(table_ref)  
        field_names = [field.name for field in table.schema if field.name != exclude_field]
        field_str = ", ".join(field_names)
        query = f"SELECT {field_str} FROM `{table_ref}`"
        return query

    client = bigquery.Client(project=project_id)

    # 제외하고자 하는 필드를 제외한 모든 필드로 쿼리를 생성합니다.
    query = create_query_exclude_field(dataset_id, table_id, exclude_field, client)

    # 쿼리를 실행하여 임시 테이블에 결과를 저장합니다.
    job_config = bigquery.QueryJobConfig(destination=client.dataset(dataset_id).table(table_id + "_temp"))
    query_job = client.query(query, job_config=job_config)
    query_job.result()  # Waits for the job to complete.

    table_ref = client.dataset(dataset_id).table(table_id + "_temp")

    # GCS로 데이터를 추출합니다.
    destination_uri = f"{gcs_output_path}/{table_id}.csv"
    extract_job = client.extract_table(
        table_ref,
        destination_uri,
        location="asia-northeast3"  # Set your dataset's location
    )
    extract_job.result()  # Waits for the job to complete
    
    # 임시 테이블을 삭제합니다.
    client.delete_table(table_ref)

    output_csv.path = destination_uri  
    print(output_csv.path)
    
    
@component(packages_to_install=["google-cloud-bigquery", "pandas"],base_image='asia-northeast3-docker.pkg.dev/GCP_PROJECT_NAME/pipeline/dataextract:1')
def extract_dictionary_to_gcs(
    project_id: str, 
    dataset_id: str, 
    table_id: str, 
    gcs_output_path: str, 
    output_csv: Output[Dataset]
):
    from google.cloud import bigquery
    client = bigquery.Client(project=project_id)

    # 테이블의 참조를 얻습니다.
    table_ref = client.dataset(dataset_id).table(table_id)

    # GCS로 데이터를 추출합니다.
    destination_uri = f"{gcs_output_path}/{table_id}.csv"
    extract_job = client.extract_table(
        table_ref,
        destination_uri,
        location="asia-northeast3"  # Set your dataset's location
    )
    extract_job.result()  # Waits for the job to complete

    output_csv.path = destination_uri 
    print(output_csv.path)

@component(base_image='asia-northeast3-docker.pkg.dev/GCP_PROJECT_NAME/bert4rec/model:cpu')
def train_model(
    data_csv_path: Input[Dataset],
    epochs: int,

):

    pass
    

@pipeline(name='bert4rec-pipeline')
def pipeline(
    project_id: str = 'GCP_PROJECT_NAME',
    dataset_id_1: str = 'GCP_BIGQUERY_OFFLINESTORE',
    table_id_1: str = 'playlist_tracks',
    dataset_id_2: str = 'GCP_BIGQUERY_OFFLINESTORE',
    table_id_2: str = 'playlist_track_dictionary',
    gcs_output_path: str = 'GCS_OUTPUT_PATH'):
    # 데이터 추출 컴포넌트
    extract_playlist_task = extract_playlists_to_gcs(
        project_id=project_id, 
        dataset_id=dataset_id_1, 
        table_id=table_id_1, 
        exclude_field='playlist_id', 
        gcs_output_path=gcs_output_path
    )
    extract_dictionary_task = extract_dictionary_to_gcs(
        project_id=project_id, 
        dataset_id=dataset_id_2, 
        table_id=table_id_2, 
        gcs_output_path=gcs_output_path
    )
    
    # 모델 학습 컴포넌트
    train_model_op = train_model(
    data_csv_path=extract_playlist_task.outputs['output_csv'],
    epochs=70)
    


# 파이프라인 컴파일
compiler.Compiler().compile(
    pipeline_func=pipeline,
    package_path='bert4rec_pipeline.json')


aip.init(
    project='GCP_PROJECT_NAME',
    location='asia-northeast3',
)

# Prepare the pipeline job
job = aip.PipelineJob(
    display_name="bert4rec-pipline",
    template_path="bert4rec_pipeline.json",
    pipeline_root='GCP_CLOUD_STORAGE_PATH',
    parameter_values={
            'project_id': 'GCP_PROJECT_NAME',
            'dataset_id_1': 'GCP_BIGQUERY_OFFLINESTORE',
            'table_id_1': 'playlist_tracks',
            'dataset_id_2': 'GCP_BIGQUERY_OFFLINESTORE',
            'table_id_2':  'playlist_track_dictionary',
            'gcs_output_path': 'GCS_OUTPUT_PATH'
        }
    )

job.submit()