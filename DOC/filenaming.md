# Guidelines for Naming Files and Folders

Guidelines for naming files and an overview of standard folders.

<!-- TOC depthFrom:2 depthTo:3 -->

- [Guidelines for Naming Files and Folders](#guidelines-for-naming-files-and-folders)
  - [Naming](#naming)
    - [Folders](#folders)
    - [Files](#files)
  - [Classes, Categories, or Types](#classes-categories-or-types)
  - [Keeping Track of Revisions](#keeping-track-of-revisions)
    - [Organize Older Versions](#organize-older-versions)
  - [Date as Description](#date-as-description)
  - [Naming Exceptions](#naming-exceptions)
  - [Unity Project Structure](#unity-project-structure)
    - [Unity Project](#unity-project)
    - [Project Source / Art Asset Production](#project-source--art-asset-production)
  - [Folder Structure (General)](#folder-structure-general)
    - [APP/](#app)
    - [/LICENSED/](#licensed)
      - [Documenting Permission](#documenting-permission)

<!-- /TOC -->

## Naming

Please use the following rules unless they break a specific application or language convention.

### Folders

1. UPPERCASE
2. Contain no spaces (use underscore)
3. Contain no special symbols such as `$ + ! # &` etc.
4. Singular

### Files

1. File names, starting from left to right, are general to specific:
    `client_project_category_description.extension`
2. lowercase
3. Contain no spaces (use underscore)
4. Contain no special symbols such as `$ + ! # &` etc.

## Classes, Categories, or Types

Externalize resources outside of the main scene 
to allow separation of workload 
and sharing of resources between scenes.

1. `ani_` - Animation data such as Alembic caches (.abc) and FBX takes. File name may include scene and shot designation.
      Example: `bbo_ani_mland_070.abc` (MLAND, shot 7)
2. `mdl_` - Model: Discreet geometry, typically with texture
    assignments, linked into scenes, found in `MODEL/`
3. `edit_` - Edit: Shot sequence; edit decision list
4. `comp_` - Composite: Typically for render-intensive animations
5. `sce_` - Scene: A collection of models and, in some cases, lights
    and cameras from which a render is made, found in `SCENE/`.
      Example: `lrl_tour_sce050_030_glr.blend` (scene 5, shot 3)
6. `tex_` - Texture: A specially prepared image, referenced by a
    material, to add detail such as a decal or pattern, found in
    `TEXTURE/`
7. `mat_` - Materials: May contain more than one material (as a
    library) and could reference external resources such as textures. Found in `MATERIAL/`
<!-- 7. `gp_` - Grease Pencil animation file. Typically organized by scene. -->

## Keeping Track of Revisions

A version control system such as [Git](https://git-scm.com/) is highly encouraged. If doing so, skip to the next section.

_When not using a version control system..._ Change both the version number and editor initials when updating a file as follows:

`..._`**`001`**`_...` indicates version; the higher the number, the more
recent the revision (increment up to 999, use three digits)

`..._001_`**`glr`**`.ext` indicates the reviser's initials (always three
characters; ends file name before extension)

Do not use date for indicating version.

**Pattern:**\

    client_project_filedescription_[###]_[aaa].extension

**Example:**\

    lrl_idy_filedescription_003_glr.docx

For persons without middle names choose z or x.

### Organize Older Versions

Older versions that you would like to get out of the way, but not delete until Close Down, can be moved to an [\_OLD](#_old-) folder at the same location.

## Date as Description

If the date is part of the file name description the following formats apply:

**Single Date pattern and example:**\

    ..._YYYY-MM-DD_...
    ..._2019-03-26_...

**Date Range pattern and examples:**\

    ..._YYYY-MM-DD--MM-DD_...
    ..._2019-03-26--04-02_...

...such as for reports:\

    lrl_ops_report_dly_2023-05-03.docx
    lrl_ops_report_qtr_2023-04-01.docx
    lrl_ops_report_wky_2023-03-26--04-02.docx

**Date + Time**\
*For multiple meetings in the same day (for the same project)*\

    Meeting Agenda 2013-03-06-0900

Please use 24 hour notation, for example, a 4pm meeting would be `1600`.

## Naming Exceptions

File and folder names may remain as-is, when generated using scripts or build process.

## Unity Project Structure

### Unity Project

```
[PROJECTNAME]_ENGINE
  └── Assets/
      └── [PROJECTNAME]
          │   ├── MODEL
          │   ├── LRL_HOUSE
          |   │   └── Materials
          |   │       └── TEXTURE
          |   └── [MODELNAME]
          |       └── Materials
          |           └── TEXTURE
          ├── SCENE
```

### Project Source / Art Asset Production

```
[PROJECTNAME]
  ├── MATERIAL
  │   └── (Substance, Blender shared materials)
  ├── MODEL
  │   └── LRL_HOUSE
  │       ├── (Blender project files)
  │       └── TEXTURE
  │           └── (kra, psd, tga, png etc.)
  └── SCRIPT
```

## Folder Structure (General)

Folder location determines scope... Folder contents are determined by their location, for example, `CLIENT_NAME/DOC`.

*In some cases you will find an established client folder will have a `GENERAL` folder within, such as `CLIENT_NAME/GENERAL`. We use this to organize more general, or shared content, such as a logo and other client-supplied content that has a larger scope than one specific project.*

### APP/

Scripts or utilities used for maintaining the project *and that are specific to* the project. Items might include scripts developed by the team to automate repetitive tasks.

This folder may also exist a level or two above the project root: `../APP/` since the contents are re-usable across more than one project, such as for SDKs (e.g. Verge3D).

### <Asset Type>/LICENSED/

Licensed material documented as indicated under *Documenting Permission*.

#### Documenting Permission

Use the following template to document the source of the licensed asset:

`TEMPLATE/licensed_source.txt`

which contains the following information:

1.  Image file name, including extension
2.  Source, such as website address
3.  License details (i.e. exactly what rights were purchased)
    1.  Date of purchase (`YYYY-MM-DD`)
    2.  Price
    3.  Duration of permission in `YYYY-MM-DD--YYYY-MM-DD` format

4.  Content of any emails granting permission (include header info such
    as sender and date.)

Invoices or other documentation may be collected in a folder, for example:

    woman-computer.jpg
    woman-computer_source/ (folder)
         woman-computer_source.txt
         woman-computer_invoice.pdf

For additional details about each folder, please refer to `DOC/folderdetails.md`

NOTE: `DOC/folderdetails.md` exists after project configuration step `make config`. See `DOC/usage.md` for more information.
