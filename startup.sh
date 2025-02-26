docker run -it \
    --restart always \
    -v "$(pwd)/cupets.json:/bot/cupets.json" \
    --name fuel-bot \
    fuel-bot