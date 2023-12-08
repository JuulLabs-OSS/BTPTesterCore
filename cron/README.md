# BTPTester Cron

#### BTPTester configuration (`sample_config.py`)

This configuration file is needed to provide the cron script
with local environment informations.

##### IUTs `auto_cfg['iuts']`

Contains informations about available IUTs.

`name` the name of the device. If the device can be flashed, this
should correspond to one of the `projects/[OS]/boards/*.py` file name.

`supported_os` array should contain OSs that can be flashed on the board.

##### Test options `auto_cfg['test_options']`

Contains the test options. For now, only specifying tests is supported.

##### OS git and path `auto_cfg['XXX']`

Contains informations about a supported OS.

`project_path` corresponds to the path where the project is located.

`git` contains all the sub-repos informations.

#### Cron configuration (`sample_cron_config.py`)

This configuration file describes the pull requests and scheduled jobs.

`email` contains the details of a smtp server to send exceptions mails.

`cyclical_jobs` contains scheduled jobs description and associated
function and options.

##### Github crons

`github_crons` contains github repos to look for pull requests and
magic words with their associated function.

`pr_repo_name_in_config` should match one of the OS defined in
`common/iutctl.py`