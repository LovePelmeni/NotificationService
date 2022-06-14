# Notification Service

---
#### docs link: [API Documentation]("http://localhost:8099/swagger/)
#### download docs: [JSON API Docs file]("http://localhost:8099/swagger/json/")

--- 

`Notification Service` - Service, responsible for Notification Delivery,
Using Firebase server as notification delivery. (Communicates via HTTP REST and Asynchronous Events via RabbitMQ queues.)


## Technologies

`PostgresSQL` as a main database.

`Firebase` as a notification server.

`Django` as a main framework.

`Nginx` as a web server.

`Gunicorn` as a proxy between application and web server.

`RabbitMQ` cluster,  integrated for distributed communication within multiple services.

--- 

## Dependencies 

`python` - 3.8 or above 

`postgressql` - 13.3 or above 

`nginx` - latest or less 

`Docker` - 1.41 or less

`Docker-Compose` - 3.9 or above

`Firebase` - have a project or create a new one.

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
---

## If Production Mode
#### Go to the `NotificationApp/project/env_file.env` and set up necessary env variables.
##### After that run docker compose file in the main directory.
```doctest
    docker-compose up -d 
```

---

## If Debug Mode

#### After all procedures that you've made before you need to run.
   
```doctest
   # Directory: NotificationService/NotificationApp/
   
   python manage.py makemigrations --database backup_database 
   python manage.py migrate 
   
   python manage.py makemigrations --database backup_database 
   python manage.py migrate 
   
   python manage.py runserver
   
   
```


## Integration via http

```doctest
    # api.py
    
    import requests 
    SERVICE_HOST = 'APPLICATION DOCKER SERVICE HOST NAME' 
    # if you run it from the other docker container
    # make sure that the host is going to be a name
    # of the docker service, "application" in the current scenario.
    # Not "localhost"
    response = requests.get('http://%s:8081/healthcheck/' % SERVICE_HOST)
    return response.json()
```
