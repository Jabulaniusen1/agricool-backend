#!/bin/bash

# Options
ENVIRONMENT=${ENVIRONMENT:-development}
DOT_ENV_FILENAME=${DOT_ENV_FILENAME:-.env.${ENVIRONMENT}}
SEED_SQL_FILE="seed_development_db.sql"

# Runtime helpers
CURRENT_DIR=$(dirname -- "$0")
MAIN_API_ROOT=$(realpath "$CURRENT_DIR/..")
SCRIPTS_ROOT="$MAIN_API_ROOT/scripts"
DOCKER_COMPOSE_ENV_FILENAME="docker-compose.${ENVIRONMENT}.yml"
PROJECT_NAME="coldtivate-$ENVIRONMENT"
DOCKER_COMPOSE_CMD="docker-compose --project-name=$PROJECT_NAME --project-directory=$MAIN_API_ROOT -f docker-compose.yml -f $DOCKER_COMPOSE_ENV_FILENAME --env-file=$DOT_ENV_FILENAME"

# Export the DOT_ENV_PATH so the docker-compose configurations can refer to it
export DOT_ENV_PATH="$MAIN_API_ROOT/$DOT_ENV_FILENAME"

# Load the environment variables
set -a && source "$DOT_ENV_PATH" && set +a

# Load default database values
DB_NAME=${DB_NAME:-base}
DB_USERNAME=${DB_USERNAME:-base}
DB_PASSWORD=${DB_PASSWORD:-base}
DB_HOST=${DB_HOST:-db}
DB_PORT=${DB_PORT:-5432}

###
## Helpers
###

_exit_with_error () {
    [ "$2" != "" ] && echo "[Error]: $2";
    exit $1;
}

_print_head() {
    cat <<EOF

Coldtivate's Environment Deployment Management script

This script handles several commands to manage a local or remote Coldtivate
environment and is intended to be used by the dev team and the CI/CD pipeline
to deploy to the existing environments.

-------------------------------------------------------------------------------
  _Settings_:

  [compose project-name]: $PROJECT_NAME
  [selected environment]: $ENVIRONMENT
  [env-specific docker-compose file]: $DOCKER_COMPOSE_ENV_FILENAME
  [env-specific dotenv file]: $DOT_ENV_FILENAME
  [seed SQL file path]: $SEED_SQL_FILE

-------------------------------------------------------------------------------

EOF
}

_database_url () {
    echo -n "postgres://${DB_USERNAME}:${DB_PASSWORD}@${DB_HOST}:${DB_PORT}/${1:-${DB_NAME}}";
}

###
## Main
###

if [ ! -f "$MAIN_API_ROOT/$DOCKER_COMPOSE_ENV_FILENAME" ]; then
    _exit_with_error 1 "Docker Compose file for this specific environment was not found!";
fi;

if [ ! -f "$MAIN_API_ROOT/$DOT_ENV_FILENAME" ]; then
    _exit_with_error 2 "DotEnv file for this specific environment was not found!";
fi;

case $1 in
    deploy)
        _print_head;

        # This will probably only be needed by dev
        $DOCKER_COMPOSE_CMD build
        # Pull the most recent images based on the given configuration
        $DOCKER_COMPOSE_CMD pull

        # Start production database if not running on production
        if [ "$ENVIRONMENT" != "production" ]; then
            echo "Starting the DB container..."
            $DOCKER_COMPOSE_CMD up --wait --detach db
        fi

        # Seed development environment
        if [ "$ENVIRONMENT" = "development" ]; then
            PSQL="$DOCKER_COMPOSE_CMD exec -T db psql";

            echo "Checking for 'seed' database..."
            if ! $PSQL -d "$(_database_url)" -tAc "SELECT 1 FROM pg_database WHERE datname = 'seed'" | grep -q 1; then
                echo "Creating and seeding 'seed' database from $SEED_SQL_FILE..."
                $PSQL -d "$(_database_url)" -c "CREATE DATABASE seed;"
                $PSQL -d "$(_database_url seed)" < "$SCRIPTS_ROOT/$SEED_SQL_FILE"
            else
                echo "'seed' database already exists."
            fi

            # Check if the DB_NAME database is empty
            if ! $PSQL -d "$(_database_url)" -tAc "SELECT 1 FROM pg_tables WHERE schemaname = 'public' LIMIT 1" | grep -q 1; then
                echo "Database $DB_NAME is empty, to recreate from seed, run the following commands:"
                echo "  1. DROP DATABASE IF EXISTS \"$DB_NAME\";"
                echo "  2. CREATE DATABASE \"$DB_NAME\" TEMPLATE seed;"
            else
                echo "Database $DB_NAME is not empty, skipping recreation from seed."
            fi
        fi

        # Execute migrations
        $DOCKER_COMPOSE_CMD run --rm web pipenv run python manage.py migrate

        # And load the necessary roles
        $DOCKER_COMPOSE_CMD run --rm web pipenv run python manage.py load_roles

        # Push Farmer and Impact dashboards views
        $DOCKER_COMPOSE_CMD run --rm farmer_web python create_view.py -v analytics_crate_movements
        $DOCKER_COMPOSE_CMD run --rm impact_dashboard_web python create_view.py -v create_relevant_checkins_view

        # We should be ready to now rollout the rest of the dependencies
        exec $DOCKER_COMPOSE_CMD up -d;

        echo "The environment was _coldtivated_ with great success! 👀"
    ;;


    compose)
        _print_head;
        exec $DOCKER_COMPOSE_CMD ${@:2};
    ;;

    manage)
        $DOCKER_COMPOSE_CMD exec web pipenv run python manage.py ${@:2};
    ;;

    sh)
        CONTAINER="${2:-web}"
        CMD="${@:3}"

        exec $DOCKER_COMPOSE_CMD exec -ti "$CONTAINER" ${CMD:-/bin/bash};
    ;;

    call_task)
        TASK_NAME=$2

        if [ "$TASK_NAME" == "" ]; then
            _exit_with_error 3 "No task name provided"
        fi

        echo "Triggering a celery task with the name $TASK_NAME"
        exec $DOCKER_COMPOSE_CMD exec celery pipenv run celery -A base.celery call "$TASK_NAME" ${@:3};
    ;;

    *)
        echo "Usage examples:";
        echo
        echo "  - deploy # Deploy the selected environment:"
        echo "    $0 deploy";
        echo
        echo "  - sh # Interactive terminal with bash or other command:"
        echo "    $0 sh # Opens up bash# on the *web* container";
        echo "    $0 sh celery # Opens up bash# on the *celery* container";
        echo "    $0 sh celery ls / # Executes *ls /* on the *celery* container";
        echo
        echo "  - manage # Access the manage.py CLI:"
        echo "    $0 manage makemigrations";
        echo "    $0 manage migrate";
        echo
        echo "  - call_task # Manually trigger a task with celery:"
        echo "    $0 call_task task_name_goes_here";
        echo
        echo "  - compose # Access to the compose command underneath:"
        echo "    $0 compose up -d";
        echo "    $0 compose exec web pipenv run python manage.py migrate";
        echo
        echo "  - ENV:DOCKER_HOST # Deploy towards a remote docker machine:"
        echo "    DOCKER_HOST=ssh://user@machine ENVIRONMENT=qa-01 $0 up";
        echo
        echo "Options:"
        echo "  deploy      Deploys a Coldtivate's environment"
        echo "  compose     Passes all the args to docker-compose"
        echo "  sh          Interactive terminal into a container"
        echo "  manage      Gives you access to the manage.py CLI"
        echo "  call_task   Manually trigger a task with celery"
        echo
        echo "© 2024 Coldtivate / YVCCA"
    ;;
esac;
