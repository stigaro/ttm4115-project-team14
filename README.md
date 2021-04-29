# ttm4115-project-team14
The repository for team 14 semester project code

Kanban board:
https://trello.com/b/5ZpPm2Fs/design-av-kommuniserende-systemer-gruppe-14

Teacher repository:
https://github.com/falkr/stmpy-notebooks

## Getting Started

### Prerequisites
- python3
- pip
- ffmpeg

### Installation

1. Clone this repo `git@github.com:stigaro/ttm4115-project-team14.git`
```sh
pip install -r requirements.txt
```

2. Start up the server by running
```sh
python ./server/server.py
```

3. Start up the client by running either `nurse_walkietalkie.py` or `patient_walkietalkie.py`
```sh
python ./client/nurse_walkietalkie.py
```

This will run both the server and the client, pressing `CTRL+C` in the terminal will exit both processes

The Walkie talkies can be runned with the options `-d` or `--debug` for debugging

## Usage

To communicate with the walkie talkie a codeword following a keyword is needed.

The codeword used to communicate with the walkie talkie is set to `Lisa` and the following keywords possible are listed under.

### Keywords

| Command       | Description                                          | Nurse | Patient |
|---------------|------------------------------------------------------|-------|---------|
| send <name>   | Send message to <name>                               | yes   |         |
| replay <name> | Request replay of the latest message from the server | yes   |         |
| play          | Play the messages in queue                           | yes   |         |
| replay        | Replay the message played in queue                   | yes   | yes     |
| next          | Iterate through the message queue                    | yes   |         |
| help          | Send message to a randomly assigned nurse            |       | yes     |
