// Runs only on first initialization of the Mongo volume.
const appDb=db.getSiblingDB('psm');
appDb.createUser({user:'psm',pwd:process.env.MONGO_APP_PASSWORD,roles:[{role:'readWrite',db:'psm'}]});
