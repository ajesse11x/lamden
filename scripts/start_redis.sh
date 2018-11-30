# Find a free port to use
port=$(python3 ./scripts/free_port.py)
pw=$(python3 ./scripts/random_password.py)

if [ -z "$CIRCLECI" ]
then
    echo "Activating virtual env"
    chmod 777 ./venv/bin/activate
    ./venv/bin/activate
    echo "echo 'HELLO HELLO I ADDED THIS TO BASH RC'" >> /root/.bashrc
    echo "echo 'HELLO HELLO I ADDED THIS TO BASH PROFILE'" >> /root/.bash_profile
fi

# Configure env files
export PYTHONPATH=$(pwd)
export REDIS_PORT=$port
export REDIS_PASSWORD=$pw

echo "
REDIS_PORT=$REDIS_PORT
REDIS_PASSWORD=$REDIS_PASSWORD
" > docker/redis.env

echo "Starting Redis server..."
redis-server
