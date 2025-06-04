# Syllabus & Task Tracker

## Description

The Syllabus & Task Tracker is a desktop application built with Python and PyQt5. It helps students or educators manage their course syllabi and track associated tasks, assignments, and lab work. The application parses syllabus information from a predefined text format, displays course details, allows users to mark ongoing chapters, and manage a to-do list of tasks with due dates and statuses.

## Features

* **Syllabus Parsing**: Automatically parses course information (title, course number, credits, units, lab work) from a structured text input.
* **Syllabus Viewer**:
    * Displays a list of all parsed subjects.
    * Shows detailed information for a selected subject, including course details, units, and laboratory work.
    * Allows users to select and track the currently ongoing chapter for each subject.
* **Task Management**:
    * Add, update, and delete tasks associated with subjects.
    * Task details include: Subject, Type (Assignment, Lab Report, etc.), Description, Date Assigned, Submit By Date, and Status (Pending, In Progress, Completed, Cancelled).
    * Tasks are displayed in a sortable table.
    * Form for easy input and modification of task details.
* **Notice Board**: Displays a summary of recent and upcoming tasks, highlighting due dates and urgency.
* **Data Persistence**:
    * Saves and loads task lists to/from a `syllabus_tasks.json` file.
    * Saves and loads ongoing chapter selections to/from an `ongoing_chapters.json` file.
* **User-Friendly Interface**: Tabbed interface for easy navigation between syllabus viewing and task management.

## How to Run

1.  **Prerequisites**:
    * Python 3.x
    * PyQt5 library

2.  **Installation**:
    * Ensure Python 3 is installed on your system.
    * Install PyQt5 using pip:
        ```bash
        pip install PyQt5
        ```

3.  **Running the Application**:
    * Save the main application code as `main.py` (or your preferred filename).
    * Ensure the `pdf_text` variable within `main.py` contains your syllabus data in the expected format.
    * Run the script from your terminal:
        ```bash
        python main.py
        ```
    * The application window will appear. If `syllabus_tasks.json` or `ongoing_chapters.json` do not exist, they will be created when you add tasks or select ongoing chapters, respectively.

## Dependencies

* **Python 3**: The core programming language.
* **PyQt5**: Used for the graphical user interface.
    * `PyQt5.QtWidgets`
    * `PyQt5.QtCore`
    * `PyQt5.QtGui`
* **Standard Python Libraries**:
    * `sys`
    * `re` (for regular expressions used in syllabus parsing)
    * `datetime`
    * `collections.defaultdict`
    * `json` (for saving and loading task/chapter data)

## File Structure (Assumed)


Syllabus_Tracker_App/
├── main.py                     # Main application script
├── syllabus_tasks.json         # Stores task data (created/updated by the app)
└── ongoing_chapters.json       # Stores ongoing chapter data (created/updated by the app)
└── README.md                   # This file


## Syllabus Text Format (within `main.py`)

The application expects the syllabus data to be embedded within the `main.py` script in a multi-line string variable named `pdf_text`. Each subject should ideally start with a line like:


Course Title: [Your Subject Title]
Course No: [Course Code]
Nature of the Course: [e.g., Theory + Lab]
Semester: [e.g., IV]
Full Marks: [e.g., 60+20+20]
Pass Marks: [e.g., 24+8+8]
Credit Hrs: [e.g., 3]

Course Description: ...
Course Objectives: ...
Course Contents:
Unit I: [Unit Name] (Hrs)
...
Laboratory Works:
...
Text Books:
...
Reference Books:
...


The parser is designed to be somewhat flexible but works best with this general structure.

## Future Enhancements (Suggestions)

* **External Syllabus File**: Load syllabus data from an external `.txt` or `.pdf` file instead of embedding it in the code.
* **PDF Parsing**: Integrate a PDF parsing library (like PyMuPDF or pdfminer.six) to directly extract text from PDF syllabus files.
* **Advanced Filtering/Sorting**: More advanced options for filtering and sorting tasks in the task manager.
* **Reminders/Notifications**: Implement system notifications for upcoming task deadlines.
* **Calendar View**: A calendar view to visualize task deadlines.
* **Themes/Customization**: Allow users to customize the application's appearance.
* **Export Tasks**: Option to export tasks to CSV or other formats.

## Author

* Aadarsha Jha
