# pathFinding Project

## Overview
The pathFinding project is a Python application designed to assist users in finding paths within a defined space. It features a graphical user interface (GUI) built using PyQt6, allowing users to interact with various tools and functionalities.

## Directory Structure
```
pathFinding
├── app
│   ├── __init__.py
│   ├── main_window.py
│   ├── widgets
│   │   ├── __init__.py
│   │   └── custom_widgets.py
│   └── tools
│       ├── __init__.py
│       └── sidebar.py
├── tests
│   └── __init__.py
├── main.py
├── requirements.txt
└── README.md
```

## Components
- **app/**: Contains the main application code.
  - **main_window.py**: Sets up the main user interface.
  - **widgets/**: Contains custom widgets used in the application.
  - **tools/**: Contains utility classes and functions, including the sidebar for tools.
  
- **tests/**: Contains unit tests for the application.
  
- **main.py**: The entry point of the application, initializing and starting the GUI.

- **requirements.txt**: Lists the dependencies required to run the application.

## Installation
To install the required dependencies, run:
```
pip install -r requirements.txt
```

## Usage
Run the application using:
```
python main.py
```

## Contributing
Contributions are welcome! Please feel free to submit a pull request or open an issue for any enhancements or bug fixes.

## License
This project is licensed under the MIT License.