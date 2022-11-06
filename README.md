# Traffic Warden game

I wrote this game as a demo for a talk I was invited to give at DevSoc (The University of York Game Dev Society)

It's a real time online multiplayer game. Similar in style to jackbox games it is played by lots of people in one room on mobile phones, along with a main view normally displayed on a big screen.

## Screenshots

<img src="/lexbailey/demo_webgame/raw/main/static/images/screenshot1.png" alt="Screenshot of traffic warden being played on a phone" width="400px">

## Installing and running

1. Clone this repo
2. Make a python venv

    `virtualenv --python=python3 venv`
    
3. Enter the venv

    `source venv/bin/activate.<something>` (changes depending on your shell, for bash use `source venv/bin/activate`)
    
4. Install the deps in the venv

    `pip install -r requirements.txt`
    
5. Configure the game

    `cp config.example.json config.json` (and then edit config.json)
    
6. Run the server

    `./server.py`
    
7. Navigate your browser to the url provided by the server

## Config

`host`: hostname or IP address to listen on (default: localhost)

`port`: port number to listen on (default: 8080)

`show_stats`: set to true to enable the "/stats" endpoint

`ext_url`: The URL used as a base for generating the join link. Required if you are running this behind a reverse proxy (defaults to 'http://{host}:{port}')
