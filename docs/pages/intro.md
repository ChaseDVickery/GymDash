# GymDash
## Table of Contents
1. [Install](getting_started/controls.md)
2. [Getting Started](#getting-started)
3. [Frontend](#usage-frontend)
    1. [Sidebar](#sidebar)
    2. [Control](#control)
    3. [Analyze](#analyze)
    4. [Configs](#configs)
4. [Backend](#usage-frontend)
    1. [Project](#projects)
    2. [Simulations]
5. [Appendix](#appendix)


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

You will need to interface with the frontend with a supported web browser that has permissions to execute JavaScript.