# {{ project_name }}

- Blender version: {{ b3d_version }}
- Godot version: {{ godot_version }}

---

This project is:

1. A reusable folder structure, 
2. suggested file naming, and 
3. tools for automation (requires 1 and 2.)

- [{{ project\_name }}](#-project_name-)
  - [Quickstart, no Git, no scripts](#quickstart-no-git-no-scripts)
  - [Quickstart](#quickstart)
  - [Quickstart, pt-cli](#quickstart-pt-cli)
    - [Customize](#customize)
  - [Included Utility Scripts](#included-utility-scripts)
  - [Example Folder Structure](#example-folder-structure)

## Quickstart, no Git, no scripts

1. Download the zip, extract and rename the top-level directory
2. Adapt [[./DOC/filenaming.md]] to your requirements
3. Delete folders and files you don't need for your project

## Quickstart

1. Clone this git repo
2. Copy and rename the folder according to your project
3. Ensure you have Python
4. Run the post_config script (`.bat` for Windows; `.sh` for Linux/macOS)

After initial project configuration, edit this _readme_ for your project. Fork the template repo to customize for your organization or team.

## Quickstart, pt-cli

```bash
npm i @garyr/pt-cli

pt learn https://github.com/garyritchie/pt_godot

pt init pt_godot ./path/to/MY_PROJECT
```

### Customize

```bash
pt init pt_godot ./path/to/MY_NEW-TEMPLATE

pt config pt_godot --json > ./path/to/MY_NEW-TEMPLATE/.pt-template.json
```

Edit the `post_config` scripts, `.pt-template.json`, and `readme.md`, then:

```bash
pt learn ./path/to/MY_NEW-TEMPLATE
```

For more information and examples see <https://github.com/garyritchie/pt-cli/blob/main/doc/usage.md>

## Included Utility Scripts

Python 3.x required to use the scripts in `./APP/`

- `python ./APP/getgodot.py -h` - For retrieving latest point-release. Symlinks it to your path.
- `python ./APP/getblender.py -h` - Same as above but for Blender.
- `python ./APP/tasks.py -h` - Work-in-progress translation of my main makefile. Relies heavily on companion `.makerc` or environment variables.

## Example Folder Structure

Placing the template as a sibling to your organizations allows `python ./APP/tasks.py update` to work from within a project folder.

For example, given the structure below, doing `python ./APP/tasks.py update` within `PROJECT_B` will pull newer shell scripts from the `PROJECT_TEMPLATE` two levels up. An `.update-exclude` in the project root will prevent listed files from getting overwritten.

Project retrospective is an opportunity to migrate time-saving improvements of tools and structure back to the template.

```bash
.
├── .env
├── ORGANIZATION_ONE/
│   ├── .env
│   ├── .makerc
│   ├── PROJECT_A/
│   └── PROJECT_B/
├── ORG_THREE/
│   ├── .env
│   ├── .makerc
│   ├── PROJECT_ONE/
│   └── PROJECT_TWO/
├── ORG_TWO/
│   ├── .env
│   ├── .makerc
│   └── PROJECT_1/
└── PROJECT_TEMPLATE/
```
