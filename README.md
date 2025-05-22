# GymDash
GymDash (originally meant to be Gymnasium Simulation Dashboard) is a simulation dashboard for keeping track of, analyzing, and
interacting with simulations, reinforcement learning projects, and other machine learning projects.

<!-- Things to add:
Overview figure just to show what the whole window looks like.


 -->

## Table of Contents
1. [Install](#installation)
2. [Getting Started](docs/pages/getting_started/01-first_steps.md)
    1. [Controls](docs/pages/getting_started/02-controls.md)
    2. [Examples](docs/pages/getting_started/03-examples.md)
3. Frontend
    1. [Sidebar](docs/pages/frontend/01-sidebar.md)
    2. [Control](docs/pages/frontend/02-control.md)
    3. [Analyze](docs/pages/frontend/03-analyze.md)
    4. [Configs](docs/pages/frontend/04-configs.md)
4. Backend
    1. [Project](docs/pages/backend/01-project.md)
    2. [Simulations](docs/pages/backend/02-simulations.md)
5. [FAQ](#naq-nobody-asked-questions)

See the [Getting Started](docs/pages/getting_started/01-first_steps.md) documentation.

## Disclaimer
This project is still IN DEVELOPMENT. Many frontend and backend features have not been finalized or thoroughly checked and may be subject to significant change at any time.


## Installation
Option 1 - Local Install: Download the project and install via pip
locally. Download the repo with:\
`git clone https://github.com/ChaseDVickery/GymDash.git`

Option 2 - pip: Download the project via pip using a full install or a minimal base install:

- **Full Installation**: Full installation includes Tensorboard, Gymnasium,
Stable Baselines, and PyTorch/Torchvision support and packages:\
`python -m pip install gymdash[full]`

- **Minimal Installation**: Minimal installation just includes the base packages
required to run the frontend and backend. The example Simulations will not
properly work without a full installation:\
`python -m pip install gymdash`


## Getting Started
### Running Locally
#### Launch GymDash
```bash
# This creates '.gymdash-projects' folder in the launching folder
# and starts a frontend HTTP server and a backend API server.
python -m gymdash.start
```
For additional launch options, see the [Appendix - Other Launch Options](#other-launch-options).
#### Navigation
Navigate your web browser to your `localhost` port `8888`: `http://127.0.0.1:8888/src/gymdash/frontend/`. This loads the HTML page used to interact with your GymDash project.

<!-- These API are
Simulations, custom simulations & registering, streamers, interactor, custom_query and add_control_request. -->

## NAQ (Nobody Asked Questions)
**Q: Is the API RESTful?**\
**A: No.** The API is not RESTful. Most importantly, the entire system is STATEFUL in that certain API calls could depend on prior API calls. This is for a couple reasons:
1. **Dynamic Project**: Users are interacting with a potentially dynamic project on the backend. It makes sense for API calls to represent all or part of the current state of the project.
2. **Lower Bandwidth**: Simulations have to potential to generate lots of logging data that should be available. To ensure we don't waste bandwidth transferring repeat data, we track which data still needs to be sent on the backend.

**Q: Why is the interface so ugly?**\
**A:** That's just like, your opinion, man. Also it's because I'm a very utilitarian designer (aside from just being not good at it), and I haven't felt the need to go full-focus on the frontend visuals because there is so much else that can change before that. There are color themes, though. You just can't select them yet. Feel free to put your own spin on it, too. You should even be able to just edit the HTML, CSS, and JavaScript behind it.