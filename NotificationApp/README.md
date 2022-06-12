# Notification Service
#### docs link: [API Documentation]("http://localhost:8099/swagger/)
#### download docs: [JSON API Docs file]("http://localhost:8099/swagger/json/")

--- 

`Notification Service` - Service, responsible for Notification Delivery,
Using Firebase server as notification delivery.

## Technologies

`PostgresSQL` as a database.

`Firebase` as a notification server.

`Django` as a main framework.

--- 

## Dependencies 

`python` - 3.8 or above 

`postgressql` - 13.3 or above 

`nginx` - latest or less 

`Docker` - 1.41 or less

`Docker-Compose` - 3.9 or above

## Usage

```bash
    git clone https://github.com/LovePelmeni/NotificationService.git
```

#### Make Sure you set up integration points for Firebase


1. #### Create New Project if you haven't yet. 

   Follow Link: [Create New Firebase Project]("http://firebase.com/)

---
2. #### Create File called `certificate.py` in NotificationApp/main dir.
   #### Create `CERTIFICATE_CREDENTIALS` const and add the payload from the `cert.json` file. 
```doctest
   #main/certificate.py
   
   CERTIFICATE_CREDENTIALS = {<payload of the file>}
```

#### Go to the `NotificationApp/NotificationApp/settings.py` and set up necessary env variables or you can set `DEBUG=True` in the top of the file.

---
3. #### Run Docker-Compose.yaml file in the root directory.
```doctest
    docker-compose up -d 
```

## Integration via http

```doctest
    import requests 
    response = 
```
