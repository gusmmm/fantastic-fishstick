# Project: Agents with state and memory

## Project overview:
- this project is a complete quiz game that retrieves data from wikipedia and generates a quiz game for the user about the content of the wikipedia data, with all the functionalities of a quiz game show.

## General Instructions:
- you have memory. Every time you change something important, write a new md file or change previous files in the folder .memory/ . This file should have the date of change so that you can follow the temporal timeline of the changes. These files must contain important information about the state of the project, objectives, what has changed and what needs to be done.
- if there is a README.MD file in the folder that contains class definitions, read it to get information about its structure and functionalities before using it.
- use logging to send important messages and describe the workflow to the terminal
- create and/ or update README.md in each folder that contains important classes to give a detailed overview of the class, its functions and important features and dependencies.
- always check the .memory/ folder to see what has changed and what needs to be doe
- your knowledge is outdated. Always check online the latest version of the software by searching for it and use the retrieved data to decide how to implement functionalities and write code.
- this project is written mostly in python 3.12. Always use the tool UV to manage dependencies, packages and run the code.
- the python coding style is by creating class-based paradigm.
- this project use a team of gemini ADK agents. It is able to manage state, short-term memory and long-term memory. See latest documentation at https://google.github.io/adk-docs/
- this project is based in this other project: https://github.com/GoogleCloudPlatform/devrel-demos/tree/main/ai-ml/python-tutor
- the session state data is stored in a local mongoDB database. Use pymongo to manage the database.
- the long-term memory uses vertex AI memory bank. Check https://cloud.google.com/vertex-ai/generative-ai/docs/agent-engine/memory-bank/overview for latest details.

