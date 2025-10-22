# run cloud tasks
[group('cloud')]
cloud: cloud-auth cloud-settings

# authenticate to cloud
[group('cloud')]
cloud-auth:
    gcloud auth login --update-adc

# enable cloud services
[group('cloud')]
cloud-services: cloud-settings
    gcloud services enable aiplatform.googleapis.com
    gcloud services enable cloudbuild.googleapis.com
    gcloud services enable run.googleapis.com

# configure cloud settings
[group('cloud')]
cloud-settings:
    gcloud config set core/project $GOOGLE_CLOUD_PROJECT
    gcloud config list

# create cloud bucket storage
[group('cloud')]
cloud-storage: cloud-settings
    gcloud storage buckets create $STAGING_BUCKET --location=$GOOGLE_CLOUD_LOCATION
