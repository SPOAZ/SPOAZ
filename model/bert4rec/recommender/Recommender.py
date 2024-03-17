import random
import numpy as np
import pandas as pd
import torch

from recommender.BERT4Rec import BERT4Rec
from recommender.data_processing import map_column, MASK, PAD


class Recommender:
    def __init__(self):
        self.idx_to_tracks = None
        self.tracks_to_idx = None
        self.model = None
        self.tracks = None

    def prepare_model(self, model_path, tracks_path="YOUR_PLAYLIST_TRACKS_PATH", ratings_path="YOUR_RATINGS_PATH"):
        ratings = pd.read_csv(ratings_path)
        ratings.sort_values(by="timestamp", inplace=True)
        ratings, mapping, inverse_mapping = map_column(ratings, col_name="track_id")
        grp_by_train = ratings.groupby(by="user_id")
        random.sample(list(grp_by_train.groups), k=10)
        self.model = BERT4Rec(
            vocab_size=len(mapping) + 2,
            lr=1e-4,
            dropout=0.3,
        )
        self.model.eval()
        self.model.load_state_dict(torch.load(model_path)["state_dict"])

        self.tracks = pd.read_csv(tracks_path)
        self.tracks_to_idx = {a: mapping[b] for a, b in zip(self.tracks.title.tolist(), self.tracks.track_id.tolist()) if
                             b in mapping}
        self.idx_to_tracks = {v: k for k, v in self.tracks_to_idx.items()}

    def predict(self, list_tracks, top_n=10):
        if self.tracks is None:
            raise Exception("Run prepare_model first before predicting")

        ids = [PAD] * (120 - len(list_tracks) - 1) + [self.tracks_to_idx[a] for a in list_tracks] + [MASK]
        src = torch.tensor(ids, dtype=torch.long).unsqueeze(0)

        with torch.no_grad():
            prediction = self.model(src)

        masked_pred = prediction[0, -1].numpy()
        sorted_predicted_ids = np.argsort(masked_pred).tolist()[::-1]
        sorted_predicted_ids = [a for a in sorted_predicted_ids if a not in ids]

        return [self.idx_to_tracks[a] for a in sorted_predicted_ids[:top_n] if a in self.idx_to_tracks]
