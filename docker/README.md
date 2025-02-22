#### Getting started

- Our artifact requires these packages: `docker`, `docker-compose`, `unzip`. Once you have them installed, you are ready to go!

- `git clone` this repo to anywhere you like with suffient space and proper permissions.

- Untar the `dbdata.tar.xz` archive to the root of cloned repo. File structure should look like this:

  ```
  LibraryMigration
  ├── dbdata
  │   ├── collection-0-2260533153475360112.wt
  │   ├── collection-0--4197376873363363615.wt
  ```

- `cd docker && ./start.sh`

- If you are working on a Linux machine with desktop environment, a jupyter lab instance should pop up in the browser; Otherwise, just open `http://127.0.0.1:8848` in your browser. (You may alter port `8848` in `docker/docker-compose.yml`)

#### Checking status

- `cd docker && docker-compose logs`

#### Stopping containers

- `cd docker && docker-compose stop`

#### Restoring data manually

- Untar the `dbdump.tar.xz` archive to the root of cloned repo. File structure should look like this:
  ```
    LibraryMigration
    ├── dbdump
    │   ├── migration_helper.wocCommit.gz
    │   ├── migration_helper.wocRepository.gz
    ```
- `rm -r dbdata/ && mkdir dbdata`
- Uncomment line 12 & 13 in`docker/docker-compose.yml`
- `cd docker && ./start.sh`, and wait the container initialization script to finish.
- If container initialization fails, it is still possible to run initialization script manually: `docker exec docker_mongo_1 /bin/bash /docker-entrypoint-initdb.d/mongodb_restore.sh`

#### Thoubleshooting

- MongoDB failed to start (exit code 100)

The MongoDB container is running with current user privileges. Check write permission of `/dbdata`.

- MongoDB Init Script was not executed (when restoring data manually)

This indicates an error occured when executing the script. Check if `LibraryMigration/dbdump` exists, `dbdata` folder is writable, and `/docker/dbinit/mongodb_recover.sh` is executable.

- MongoDB failed to start on Windows/macOS machines

According to [MongoDB Docs](https://docs.mongodb.com/manual/administration/production-notes/#fsync---on-directories), MongoDB may run into compatibility issues working with Windows/macOS file systems. You may have to create a named volume (see `docker volume create`) and map it to `/data/db` in `docker/docker-compose.yml`, and restore data manually. 

