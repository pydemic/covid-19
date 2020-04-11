#!/bin/sh

# https://github.com/SvanBoxel/gitlab-mirror-and-ci-action/blob/master
set -u

DEFAULT_POLL_TIMEOUT=10
POLL_TIMEOUT=${POLL_TIMEOUT:-$DEFAULT_POLL_TIMEOUT}

sh -c "git clone --single-branch --branch ${GITHUB_REF:11} https://github.com/pydemic/covid-19 ../repo"

cd ../repo

branch=$(git symbolic-ref --short HEAD)

sh -c "git config --global credential.username $GITLAB_USERNAME"
sh -c "git config --global core.askPass /cred-helper.sh"
sh -c "git config --global credential.helper cache"
sh -c "git remote add mirror https://gitlab.com/pydemic/covid-19"
sh -c "git push --force mirror $branch"

sleep $POLL_TIMEOUT

pipeline_id=$(curl --header "PRIVATE-TOKEN: $GITLAB_PASSWORD" --silent "https://gitlab.com/api/v4/projects/18009503/repository/commits/${branch}" | jq '.last_pipeline.id')

echo "Triggered CI for branch ${branch}"
echo "Working with pipeline id #${pipeline_id}"
echo "Poll timeout set to ${POLL_TIMEOUT}"

ci_status="pending"

until [[ "$ci_status" != "pending" && "$ci_status" != "running" ]]
do
   sleep $POLL_TIMEOUT
   ci_output=$(curl --header "PRIVATE-TOKEN: $GITLAB_PASSWORD" --silent "https://gitlab.com/api/v4/projects/18009503/pipelines/${pipeline_id}")
   ci_status=$(jq -n "$ci_output" | jq -r .status)
   ci_web_url=$(jq -n "$ci_output" | jq -r .web_url)

   echo "Current pipeline status: ${ci_status}"
   if [ "$ci_status" = "running" ]
   then
     echo "Checking pipeline status..."
     curl -d '{"state":"pending", "target_url": "'${ci_web_url}'", "context": "gitlab-ci"}' -H "Authorization: token ${GITHUB_TOKEN}"  -H "Accept: application/vnd.github.antiope-preview+json" -X POST --silent "https://api.github.com/repos/${GITHUB_REPOSITORY}/statuses/${GITHUB_SHA}"  > /dev/null
   fi
done

echo "Pipeline finished with status ${ci_status}"

if [ "$ci_status" = "success" ]
then
  curl -d '{"state":"success", "target_url": "'${ci_web_url}'", "context": "gitlab-ci"}' -H "Authorization: token ${GITHUB_TOKEN}"  -H "Accept: application/vnd.github.antiope-preview+json" -X POST --silent "https://api.github.com/repos/${GITHUB_REPOSITORY}/statuses/${GITHUB_SHA}"
  exit 0
elif [ "$ci_status" = "failed" ]
then
  curl -d '{"state":"failure", "target_url": "'${ci_web_url}'", "context": "gitlab-ci"}' -H "Authorization: token ${GITHUB_TOKEN}"  -H "Accept: application/vnd.github.antiope-preview+json" -X POST --silent "https://api.github.com/repos/${GITHUB_REPOSITORY}/statuses/${GITHUB_SHA}"
  exit 1
fi
