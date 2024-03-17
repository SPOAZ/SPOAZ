# Use an official Python runtime as a parent image
FROM --platform=linux/amd64 python:3.8-slim

# Set the working directory in the container to /app
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY . .
# Install any needed packages specified in requirements.txt
# RUN apt-get update \
#    && apt-get install -y gcc python3.8-dev \
#    && pip install --no-cache-dir -r requirements.txt \
#    && apt-get purge -y --auto-remove gcc python3.8-dev \
#    && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir -r requirements.txt 

RUN chmod +x recommender/training.py

# Run training.py when the container launches
ENTRYPOINT ["python3.8", "recommender/training.py", "--data_csv_path","YOUR_PLAYLIST_TRACKS.csv"]
