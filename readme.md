# {{ project_name }}

- Blender version: {{ b3d_version }}
- Godot version: {{ godot_version }}

---

This project is:

1. A reusable folder structure, 
2. suggested file naming, and 
3. tools for automation (requires 1 and 2.)

- [{{ project\_name }}](#-project_name-)
  - [Quickstart, folders only](#quickstart-folders-only)
  - [Quickstart](#quickstart)
  - [Recommended](#recommended)
  - [Example Folder Structure](#example-folder-structure)

## Quickstart, folders only

1. Copy the folders you'll use in your project
2. Copy, and adapt [[./DOC/filenaming.md]] to your requirements

## Quickstart

1. Clone this git repo
2. Copy `PROJECT_TEMPLATE` and rename the folder according to your project
3. Ensure you have the _requirements_ (see below)
4. Run the config script

After initial project configuration, edit this _readme_ for your project. Fork the PROJECT_TEMPLATE repo to customize for your organization or team.

## Recommended

To get the most out of this template:

- [pt-cli](https://github.com/garyritchie/pt-cli) - Useful for template management
- Python 3.x - To use the scripts in `./APP/`

## Example Folder Structure

Placing the template as a sibling to your organizations allows `make update` to work from within a project folder.

For example, given the structure below, doing `make update` within `PROJECT_B` will pull newer makefiles and bash scripts from the `PROJECT_TEMPLATE` two levels up.

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
└── THIS_TEMPLATE/
```
