
# REMEMBER TO INCLUDE dashboard/.env FILE IN .GITIGNORE

#everytime you start working on the project, run:
docker compose up -d
cd dashboard/
npm run dev -- --open

# start the setup and create the DB:
docker compose up -d #this is to be run everytime you start working on the project
#docker compose exec -i db createdb -U postgres diffCellSig #this needed to be run only once, then DB will be created and persist across sessions

#check that DB exists (password is 'postgres')
#this is optional to check that DB exists and you can connect to it
psql -h localhost -p 5436 -U postgres
\l
\c diffCellSig

# ingest data and populate tables:
# activate the python venv if necessary
source cellSigPyVenv/bin/activate
#run the script for ingestion
python3 -m dbSetup.ingest 

# check DB through pgAdmin and puppygraph:
#puppygraph connection is at localhost:8081
curl -XPOST -H "content-type: application/json" --data-binary @./dbSetup/schema.json --user "puppygraph:puppygraph123" localhost:8081/schema


#when you finish work session, run this command to shut down containers properly
sudo docker compose down --volumes --remove-orphans

