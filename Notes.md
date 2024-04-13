- Set envs in env folder

- docker-compose up --build

- in other terminal:
docker-compose exec web python manage.py migrate
docker-compose exec web python manage.py createsuperuser


-- if you USE_S3 you need to collectstatic
docker-compose exec web python manage.py collectstatic
