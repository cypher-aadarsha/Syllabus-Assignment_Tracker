import sys
import re
import datetime
from collections import defaultdict
import json  # For potentially saving/loading tasks later

# Import necessary PyQt5 components
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTabWidget, QListWidget, QLabel, QTextEdit, QFormLayout,
    QLineEdit, QPushButton, QDateEdit, QComboBox, QTableView,
    QGroupBox, QMessageBox, QSplitter, QHeaderView, QAbstractItemView
)
# Import QtCore explicitly for QDate, Qt, QAbstractTableModel, QVariant, QModelIndex
from PyQt5.QtCore import Qt, QDate, QAbstractTableModel, QVariant, QModelIndex, pyqtSignal
from PyQt5.QtGui import QFont


# --- Syllabus Parsing Logic ---
def parse_syllabus(text):
    """
    Parses the syllabus text.

    Args:
        text (str): The full text content from the PDF.

    Returns:
        dict: A dictionary where keys are course titles and values are
              dictionaries containing course details.
    """
    syllabus_data = defaultdict(lambda: {"Units": [], "Lab Work": "", "Details": {}})
    current_subject = None
    parsing_contents = False
    current_unit_content = []
    lines = text.split('\n')
    line_idx = 0

    # Pattern for "Course Title: ..."
    course_title_pattern = re.compile(r"^\s*\"?Course Title:\s*(.*?)\"?\s*$", re.IGNORECASE)
    # General pattern for potential titles (if not starting with "Course Title:")
    # This pattern is kept simpler; relies on subsequent keyword checks.
    general_title_pattern = re.compile(r"^\s*\"?([A-Z][A-Za-z0-9\s\(\)\-\:]+?)\"?\s*$")

    detail_keywords_re = re.compile(r"Course No:|Nature of the Course:|Semester:|Full Marks:|Pass Marks:|Credit Hrs:",
                                    re.IGNORECASE)
    unit_start_re = re.compile(r"^\s*Unit\s+[IVXLCDM]+[:\s(]", re.IGNORECASE)
    lab_work_start_re = re.compile(r"^\s*(Laboratory Works?:|Lab Work:)", re.IGNORECASE)
    books_start_re = re.compile(r"^\s*(Text Books?:|Reference Books?:)", re.IGNORECASE)

    while line_idx < len(lines):
        line = lines[line_idx].strip()
        potential_title = None
        title_found_this_iteration = False

        # Try to match "Course Title: <Name>"
        match = course_title_pattern.match(line)
        if match:
            potential_title = match.group(1).strip()
            # Check if details follow in the next few lines
            for i in range(line_idx, min(line_idx + 4, len(lines))):  # Check current and next 3 lines
                if detail_keywords_re.search(lines[i]):
                    title_found_this_iteration = True
                    break

        # If not found, try to match a general title format
        # This is more heuristic: looks for a capitalized line followed by detail keywords
        if not title_found_this_iteration:
            match = general_title_pattern.match(line)
            if match:
                temp_title = match.group(1).strip()
                # Avoid matching things like "Unit I" or "Text Books:" as titles
                if len(temp_title) > 4 and not unit_start_re.match(temp_title) \
                        and not lab_work_start_re.match(temp_title) \
                        and not books_start_re.match(temp_title) \
                        and not detail_keywords_re.search(temp_title):
                    # Check if detail keywords (especially "Course No:") follow soon
                    for i in range(line_idx + 1, min(line_idx + 4, len(lines))):
                        if lines[i].strip().startswith("Course No:"):
                            potential_title = temp_title
                            title_found_this_iteration = True
                            break

        if title_found_this_iteration and potential_title:
            if current_subject and current_unit_content:  # Save previous unit
                unit_text = "\n".join(current_unit_content).strip()
                if unit_text: syllabus_data[current_subject]["Units"].append(unit_text)
            current_unit_content = []

            current_subject = potential_title
            parsing_contents = False
            syllabus_data[current_subject]  # Ensure key exists

            # Extract details from the vicinity of the title
            details_text_block = []
            for i in range(line_idx, min(line_idx + 7, len(lines))):  # Look in a small block of lines
                details_text_block.append(lines[i])
                if len(details_text_block) > 1 and lines[i].strip() == "" and \
                        (i + 1 < len(lines) and (
                                course_title_pattern.match(lines[i + 1]) or general_title_pattern.match(
                            lines[i + 1]))):  # Stop if next title seems to start
                    break
            details_text = "\n".join(details_text_block)

            # More robust detail extraction
            course_no = re.search(r"Course No:\s*(\S+)", details_text, re.IGNORECASE)
            if course_no: syllabus_data[current_subject]["Details"]["Course No"] = course_no.group(1)

            credit_hrs = re.search(r"Credit Hrs:\s*(\S+)", details_text, re.IGNORECASE)
            if credit_hrs: syllabus_data[current_subject]["Details"]["Credit Hrs"] = credit_hrs.group(1)

            semester = re.search(r"Semester:\s*(\S+)", details_text, re.IGNORECASE)
            if semester: syllabus_data[current_subject]["Details"]["Semester"] = semester.group(1)

            full_marks = re.search(r"Full Marks:\s*(\S+)", details_text, re.IGNORECASE)
            if full_marks: syllabus_data[current_subject]["Details"]["Full Marks"] = full_marks.group(1)

            pass_marks = re.search(r"Pass Marks:\s*(\S+)", details_text, re.IGNORECASE)
            if pass_marks: syllabus_data[current_subject]["Details"]["Pass Marks"] = pass_marks.group(1)

            nature = re.search(r"Nature of the Course:\s*(.+)", details_text, re.IGNORECASE)
            if nature: syllabus_data[current_subject]["Details"]["Nature"] = nature.group(1).strip()


        elif line.startswith("Course Contents:"):
            if current_subject:
                parsing_contents = True
                if current_unit_content:  # Save any lingering unit content before starting new ones
                    unit_text = "\n".join(current_unit_content).strip()
                    if unit_text: syllabus_data[current_subject]["Units"].append(unit_text)
                current_unit_content = []


        elif parsing_contents and current_subject and unit_start_re.match(line):
            if current_unit_content:
                unit_text = "\n".join(current_unit_content).strip()
                if unit_text: syllabus_data[current_subject]["Units"].append(unit_text)
            current_unit_content = [line]

        elif lab_work_start_re.match(line) and current_subject:
            if current_unit_content:  # Save previous unit
                unit_text = "\n".join(current_unit_content).strip()
                if unit_text: syllabus_data[current_subject]["Units"].append(unit_text)
            current_unit_content = []
            parsing_contents = False  # Lab work is usually after units

            lab_desc = [
                line.replace(lab_work_start_re.match(line).group(0), "").strip()]  # Remove "Laboratory Works:" prefix
            temp_idx = line_idx + 1
            blank_line_count = 0
            while temp_idx < len(lines):
                next_line = lines[temp_idx].strip()
                if not next_line:
                    blank_line_count += 1
                    if blank_line_count >= 2: break  # Stop after two consecutive blank lines
                else:
                    blank_line_count = 0

                # Stop conditions for lab work description
                if books_start_re.match(next_line) or \
                        course_title_pattern.match(next_line) or \
                        (general_title_pattern.match(next_line) and \
                         temp_idx + 1 < len(lines) and lines[temp_idx + 1].strip().startswith("Course No:")):
                    break
                lab_desc.append(next_line)
                temp_idx += 1
            syllabus_data[current_subject]["Lab Work"] = "\n".join(
                filter(None, lab_desc)).strip()  # Filter out empty strings
            line_idx = temp_idx - 1  # Adjust line_idx as we've looked ahead

        elif parsing_contents and current_subject and current_unit_content and line:
            # Append line to current unit if it seems to be part of it
            # (e.g., indented, or not starting a new major section)
            if re.match(r"^\s*\d+\.\d+(\.\d+)*\s+", line) or \
                    re.match(r"^\s*[a-zA-Z][.)]\s+", line) or \
                    (line.startswith("  ") or line.startswith("\t")) or \
                    not (unit_start_re.match(line) or lab_work_start_re.match(line) or books_start_re.match(
                        line) or course_title_pattern.match(line)):
                current_unit_content.append(line)
            else:  # Line doesn't seem part of current unit, save current unit and re-evaluate line
                if current_unit_content:
                    unit_text = "\n".join(current_unit_content).strip()
                    if unit_text: syllabus_data[current_subject]["Units"].append(unit_text)
                current_unit_content = []
                line_idx -= 1  # Re-process this line in the next iteration

        line_idx += 1

    if current_subject and current_unit_content:  # Save the last unit
        unit_text = "\n".join(current_unit_content).strip()
        if unit_text: syllabus_data[current_subject]["Units"].append(unit_text)

    # Final cleanup: remove subjects with no substantial content
    cleaned_data = {
        k: v for k, v in syllabus_data.items()
        if v.get("Units") or v.get("Lab Work") or (v.get("Details") and v["Details"].get("Course No"))
    }
    for k in cleaned_data:  # Ensure "Units" key exists even if empty
        if "Units" not in cleaned_data[k]:
            cleaned_data[k]["Units"] = []
    return cleaned_data


# --- Extracted Text (Paste the full text from the PDF here) ---
# Cleaned up entries for Operating Systems and Database Management System
pdf_text = """
--- PAGE 1 ---

Course Title: Theory of Computation
Course No: CSC257
Nature of the Course: Theory + Lab
Semester: IV
Full Marks: $60+20+20$
Pass Marks: $24+8+8$
Credit Hrs: 3

Course Description: This course presents a study of Finite State Machines and their languages.
It covers the details of finite state automata, regular expressions, context free grammars. More,
the course includes design of the Push-down automata and Turing Machines. The course also
includes basics of undecidabilty and intractability.

Course Objectives: The main objective of the course is to introduce concepts of the models of
computation and formal language approach to computation. The general objectives of this
course are to, introduce concepts in automata theory and theory of computation, design different
finite state machines and grammars and recognizers for different formal languages, identify
different formal language classes and their relationships, determine the decidability and
intractability of computational problems.

Course Contents:

Unit I: Basic Foundations (3 Hrs.)
1.1. Review of Set Theory, Logic, Functions, Proofs
1.2. Automata, Computability and Complexity: Complexity Theory, Computability Theory,
Automata Theory
1.3. Basic concepts of Automata Theory: Alphabets, Power of Alphabet, Kleen Closure
Alphabet, Positive Closure of Alphabet, Strings, Empty String, Substring of a string,
Concatenation of strings, Languages, Empty Language

Unit II: Introduction to Finite Automata (8 Hrs.)
2.1 Introduction to Finite Automata, Introduction of Finite State Machine
2.2 Deterministic Finite Automata (DFA), Notations for DFA, Language of DFA, Extended
Transition Function of DFA Non-Deterministic Finite Automaton (NFA), Notations for
NFA, Language of NFA, Extended Transition
2.3 Equivalence of DFA and NFA, Subset-Construction
2.4 Method for reduction of NFA to DFA, Theorems for equivalence of Language accepted
by DFA and NFA
2.5 Finite Automaton with Epsilon Transition (ε - NFA), Notations for  NFA, Epsilon
Closure of a State, Extended Transition Function of  NFA, Removing Epsilon
Transition using the concept of Epsilon Closure, Equivalence of NFA and  -NFA,
Equivalence of DFA and  - NFA
2.6 Finite State Machines with output: Moore machine and Mealy Machines

Unit III: Regular Expressions (6 Hrs.)
3.1 Regular Expressions, Regular Operators, Regular Languages and their applications,
Algebraic Rules for Regular Expressions

36


--- PAGE 2 ---

3.2 Equivalence of Regular Expression and Finite Automata, Reduction of Regular
Expression to  – NFA, Conversion of DFA to Regular Expression
3.3 Properties of Regular Languages, Pumping Lemma, Application of Pumping Lemma,
Closure Properties of Regular Languages over (Union, Intersection, Complement)
Minimization of Finite State Machines: Table Filling Algorithm

Unit IV: Context Free Grammar (9 Hrs.)
4.1 Introduction to Context Free Grammar (CFG), Components of CFG, Use of CFG,
Context Free Language (CFL)
4.2 Types of derivations: Bottomup and Topdown approach, Leftmost and Rightmost,
Language of a grammar
4.3 Parse tree and its construction, Ambiguous grammar, Use of parse tree to show ambiguity
in grammar
4.4 Regular Grammars: Right Linear and Left Linear, Equivalence of regular grammar and
finite automata
4.5 Simplification of CFG: Removal of Useless symbols, Nullable Symbols, and Unit
Productions, Chomsky Normal Form (CNF), Greibach Normal Form (GNF), Backus-
Naur Form (BNF)
4.6 Context Sensitive Grammar, Chomsky Hierarchy Pumping Lemma for CFL, Application
of Pumping Lemma, Closure Properties of CFL

Unit V: Push Down Automata (7 Hrs.)
5.1 Introduction to Push Down Automata (PDA), Representation of PDA, Operations of
PDA, Move of a PDA, Instantaneous Description for PDA
5.2 Deterministic PDA, Non Deterministic PDA, Acceptance of strings by PDA, Language
of PDA
5.3 Construction of PDA by Final State, Construction of PDA by Empty Stack,
5.4 Conversion of PDA by Final State to PDA accepting by Empty Stack and vice-versa,
Conversion of CFG to PDA, Conversion of PDA to CFG

Unit VI: Turing Machines (10 Hrs.)
6.1 Introduction to Turing Machines (TM), Notations of Turing Machine, Language of a
Turing Machine, Instantaneous Description for Turing Machine, Acceptance of a string
by a Turing Machines
6.2 Turing Machine as a Language Recognizer, Turing Machine as a Computing Function,
Turing Machine with Storage in its State, Turing Machine as a enumerator of stings of a
language, Turing Machine as Subroutine
6.3 Turing Machine with Multiple Tracks, Turing Machine with Multiple Tapes, Equivalence
of Multitape-TM and Multitrack-TM, Non-Deterministic Turing Machines, Restricted
Turing Machines: With Semi-infinite Tape, Multistack Machines, Counter Machines
6.4 Curch Turing Thesis, Universal Turing Machine, Turing Machine and Computers,
Encoding of Turing Machine, Enumerating Binary Strings, Codes of Turing Machine,
Universal Turing Machine for encoding of Turing Machine

37


--- PAGE 3 ---

Unit VII: Undecidability and Intractability (5 Hrs.)
7.1 Computational Complexity, Time and Space complexity of A Turing Machine,
Intractability
7.2 Complexity Classes, Problem and its types: Absract, Decision, Optimization
7.3 Reducibility, Turing Reducible, Circuit Satisfiability, Cook's Theorem,
7.4 Undecidability, Undecidable Problems: Post's Correspondence Problem, Halting
Problem and its proof, Undecidable Problem about Turing Machines

Laboratory Works:
The laboratory work consists of design and implementation of finite state machines like DFA,
NFA, PDA, and Turing Machine. Students are highly recommended to construct Tokenizers/
Lexers over/for some language. Students are advised to use regex and Perl (for using regular
expressions), or any other higher level language for the laboratory works.

Text Books:
1. John E. Hopcroft, Rajeev Motwani, Jeffrey D. Ullman, Introduction to Automata
Theory, Languages, and Computation, 3rd Edition, Pearson - Addison-Wesley.

Reference Books:
1. Harry R. Lewis and Christos H. Papadimitriou, Elements of the Theory of Computation,
$2^{nd}$ Edition, Prentice Hall.
2. Michael Sipser, Introduction to the Theory of Computation, $3^{rd}$ Edition, Thomson Course
Technology
3. Efim Kinber, Carl Smith, Theory of Computing: A Gentle introduction, Prentice- Hall.
4. John Martin, Introduction to Languages and the Theory of Computation, 3rd Edition, Tata
McGraw Hill.
5. Kenneth H. Rosen, Discrete Mathematics and its Applications to Computers Science,
WCB/Mc-Graw Hill.

38


--- PAGE 4 ---

Course Title: Computer Networks
Course No: CSC258
Nature of the Course: Theory + Lab
Semester: IV
Full Marks: $60+20+20$
Pass Marks: $24+8+8$
Credit Hrs: 3

Course Description: This course introduces concept of computer networking and discuss the
different layers of networking model.

Course Objective: The main objective of this course is to introduce the understanding of the
concept of computer networking with its layers, topologies, protocols & standards, IPv4/IPv6
addressing, Routing and Latest Networking Standards

Course Contents:

Unit 1: Introduction to Computer Network (6Hrs.)
1.1. Definitions, Uses, Benefits
1.2. Overview of Network Topologies (Star, Tree, Bus,...)
1.3. Overview of Network Types (PAN, LAN, CAN, MAN,...)
1.4. Networking Types (Client/Server, P2P)
1.5. Overview of Protocols and Standards
1.6. OSI Reference Model
1.7. TCP/IP Models and its comparison with OSI.
1.8. Connection and Connection-Oriented Network Services
1.9. Internet, ISPs, Backbone Network Overview

Unit 2: Physical Layer and Network Media (4Hrs.)
2.1. Network Devices: Repeater, Hub, Switch, Bridge, Router
2.2. Different types of transmission medias (wired: twisted pair, coaxial, fiber optic, Wireless:
Radio waves, micro waves, infrared)
2.3. Ethernet Cable Standards (UTP & Fiber cable standards)
2.4. Circuit, Message & Packet Switching
2.5. ISDN: Interface and Standards

Unit 3: Data Link Layer (8Hrs.)
3.1. Function of Data Link Layer (DLL)
3.2. Overview of Logical Link Control (LLC) and Media Access Control (MAC)
3.3. Framing and Flow Control Mechanisms
3.4. Error Detection and Correction techniques
3.5. Channel Allocation Techniques (ALOHA, Slotted ALOHA)
3.6. Ethernet Standards (802.3 CSMA/CD, 802.4 Token Bus, 802.5 Token Ring)
3.7. Wireless LAN: Spread Spectrum, Bluetooth, Wi-Fi
3.8. Overview Virtual Circuit Switching, Frame Relay& ATM
3.9. DLL Protocol: HDLC, PPP

39


--- PAGE 5 ---

Unit 4: Network Layer (10Hrs.)
4.1. Introduction and Functions
4.2. IPv4 Addressing & Sub-netting
4.3. Class-full and Classless Addressing
4.4. IPv6 Addressing and its Features
4.5. IPv4 and IPv6 Datagram Formats
4.6. Comparison of IPv4 and IPv6 Addressing
4.7. Example Addresses: Unicast, Multicast and Broadcast
4.8. Routing
4.8.1. Introduction and Definition
4.8.2. Types of Routing (Static vs Dynamic, Unicast vs Multicast, Link State vs
Distance Vector, Interior vs Exterior)
4.8.3. Path Computation Algorithms: Bellman Ford, Dijkstra's
4.8.4. Routing Protocols: RIP, OSPF & BGP
4.9. Overview of IPv4 to IPv6 Transition Mechanisms
4.10. Overview of ICMP/ICMPv6&NATing
4.11. Overview of Network Traffic Analysis
4.12. Security Concepts: Firewall & Router Access Control

Unit 5: Transport Layer (6Hrs.)
5.1. Introduction, Functions and Services
5.2. Transport Protocols: TCP, UDP and Their Comparisons
5.3. Connection Oriented and Connectionless Services
5.4. Congestion Control: Open Loop & Closed Loop, TCP Congestion Control
5.5. Traffic Shaping Algorithms: Leaky Bucket & Token Bucket
5.6. Queuing Techniques for Scheduling
5.7. Introduction to Ports and Sockets, Socket Programming

Unit 6: Application Layer (7Hrs.)
6.1. Introduction and Functions
6.2. Web &HTTP
6.3. DNS and the Query Types
6.4. File Transfer and Email Protocols: FTP, SFTP, SMTP, IMAP, POP3
6.5. Overview of Application Server Concepts: Proxy, Web, Mail
6.6. Network Management: SNMP

Unit 7: Multimedia & Future Networking (4Hrs.)
7.1. Overview Multimedia Streaming Protocols: SCTP
7.2. Overview of SDN and its Features, Data and Control Plane
7.3. Overview of NFV
7.4. Overview of NGN

Laboratory Works:
The lab activities under this subject should accommodate at least the following;
1. Understanding of Network equipment, wiring in details
2. OS (Ubuntu/CentOS/Windows) installation, practice on basic Networking commands

40


--- PAGE 6 ---

(ifconfig/ipconfig, tcpdump, netstat, dnsip, hostname, route...)
3. Overview of IP Addressing and sub-netting, static ip setting on Linux/windows machine,
testing
4. Introduction to Packet Tracer, creating of a LAN and connectivity test in the LAN,
creation of VLAN and VLAN trunking.
5. Basic Router Configuration, Static Routing Implementation
6. Implementation of Dyanmic/interior/exterior routing (RIP, OSPF, BGP)
7. Firewall Implementation, Router Access Control List (ACL)
8. Packet capture and header analysis by wire-shark (TCP, UDP, IP)
9. DNS, Web, FTP server configuration (shall use packet tracer, GNS3)
10. Case Study: Network Operation Center Visit (ISP, Telecom, University Network)
11. LAB Exam, Report and VIVA

Text Books:
1. Data Communications and Networking, 4th Edition, Behrouz A Forouzan. McGraw-Hill
2. Computer Networking; A Top Down Approach Featuring The Internet, 2nd Edition,
Kurose James F., Ross W. Keith PEARSON EDUCATION ASIA

41


--- PAGE 7 ---

Course Title: Operating Systems
Course No: CSC259
Nature of the Course: Theory + Lab
Semester: IV
Full Marks: $60+20+20$
Pass Marks: 24+8+8
Credit Hrs: 3

Course Description: This course includes the basic concepts of operating system components. It
consists of process management, deadlocks and process synchronization, memory management
techniques, File system implementation, and I/O device management principles. It also includes
case study on Linux operating system.

Course Objectives:
• Describe need and role of operating system.
• Understand OS components such a scheduler, memory manager, file system handlers and
I/O device managers.
• Analyze and criticize techniques used in OS components
• Demonstrate and simulate algorithms used in OS components
• Identify algorithms and techniques used in different components of Linux

Course Contents:

Unit 1: Operating System Overview (4 Hrs.)
1.1. Definition, Two views of operating system, Evolution of operating system, Types of OS.
1.2. System Call, Handling System Calls, System Programs, Operating System Structures,
The Shell, Open Source Operating Systems

Unit 2: Process Management (10 Hrs.)
2.1. Process vs Program, Multiprogramming, Process Model, Process States, Process Control
Block.
2.2. Threads, Thread vs Process, User and Kernel Space Threads.
2.3. Inter Process Communication, Race Condition, Critical Section
2.4. Implementing Mutual Exclusion: Mutual Exclusion with Busy Waiting (Disabling
Interrupts, Lock Variables, Strict Alteration, Peterson's Solution, Test and Set Lock),
Sleep and Wakeup, Semaphore, Monitors, Message Passing,
2.5. Classical IPC problems: Producer Consumer, Sleeping Barber, Dining Philosopher
Problem
2.6. Process Scheduling: Goals, Batch System Scheduling (First-Come First-Served, Shortest
Job First, Shortest Remaining Time Next), Interactive System Scheduling (Round-Robin
Scheduling, Priority Scheduling, Multiple Queues), Overview of Real Time System
Scheduling

Unit 3: Process Deadlocks (6 Hrs.)
3.1. Introduction, Deadlock Characterization, Preemptable and Non-preemptable Resources,
Resource - Allocation Graph, Conditions for Deadlock

42


--- PAGE 8 ---

3.2. Handling Deadlocks: Ostrich Algorithm, Deadlock prevention, Deadlock Avoidance,
Deadlock Detection (For Single and Multiple Resource Instances), Recovery From
Deadlock (Through Preemption and Rollback)

Unit 4: Memory Management (8 Hrs.)
4.1. Introduction, Monoprogramming VS. Multi-programming, Modelling
Multiprogramming, Multiprogramming with fixed and variable partitions, Relocation
and Protection.
4.2. Memory management (Bitmaps & Linked-list), Memory Allocation Strategies
4.3. Virtual memory: Paging, Page Table, Page Table Structure, Handling Page Faults,
TLB's
4.4. Page Replacement Algorithms: FIFO, Second Chance, LRU, Optimal, LFU, Clock, WS-
Clock, Concept of Locality of Reference, Belady's Anomaly
4.5. Segmentation: Need of Segmentation, its Drawbacks, Segmentation with Paging(MULTICS)

Unit 5: File Management (6 Hrs.)
5.1. File Overview: File Naming, File Structure, File Types, File Access, File Attributes, File
Operations, Single Level, two Level and Hierarchical Directory Systems, File System
Layout.
5.2. Implementing Files: Contiguous allocation, Linked List Allocation, Linked List
Allocation using Table in Memory, Inodes.
5.3. Directory Operations, Path Names, Directory Implementation, Shared Files
5.4. Free Space Management: Bitmaps, Linked List

Unit 6: Device Management (6 Hrs.)
6.1. Classification of IO devices, Controllers, Memory Mapped IO, DMA Operation,
Interrupts
6.2. Goals of IO Software, Handling IO(Programmed IO, Interrupt Driven IO, IO using
DMA), IO Software Layers (Interrupt Handlers, Device Drivers)
6.3. Disk Structure, Disk Scheduling (FCFS, SSTF, SCAN, CSCAN, LOOK, CLOOK), Disk
Formatting (Cylinder Skew, Interleaving, Error handling), RAID

Unit 7: Linux Case Study (5 Hrs.)
7.1 History, Kernel Modules, Process Management, Scheduling, Inter-process
Communication, Memory Management, File System Management Approaches, Device
Management Approaches.

Laboratory Works:
The laboratory work includes solving problems in operating system. The lab work should include
at least;
Learn basic Linux Commands
Create process, threads and implement IPC techniques
Simulate process Scheduling algorithms and deadlock detection algorithms
Simulate page replacement algorithms
Simulate free space management techniques and disk scheduling algorithms.

43


--- PAGE 9 ---

Text Books:
1. Modern Operating Systems: Andrew S. Tanenbaum, PH1 Publication, Third edition,
2008

Reference Books:
1. Abraham Silberschatz, Peter Baer Galvin and Greg Gagne, "Operating System
Concepts", John Wiley & Sons (ASIA) Pvt. Ltd, Seventh edition, 2005.
2. Harvey M. Deitel, Paul J. Deitel, and David R. Choffnes, "Operating Systems, Prentice
Hall, Third edition, 2003.

44


--- PAGE 10 ---

Course Title: Database Management System
Course No: CSC260
Nature of the Course: Theory + Lab
Semester: IV
Full Marks: $60+20+20$
Pass Marks: $24+8+8$
Credit Hrs: 3

Course Description: The course covers the basic concepts of databases, database system
concepts and architecture, data modeling using ER diagram, relational model, SQL, relational
algebra and calculus, normalization, transaction processing, concurrency control, and database
recovery.

Course Objective: The main objective of this course is to introduce the basic concepts of
database, data modeling techniques using entity relationship diagram, relational algebra and
calculus, basic and advanced features SQL, normalization, transaction processing, concurrency
control, and recovery techniques.

Course Contents:

Unit 1: Database and Database Users (2 Hrs.)
Introduction; Characteristics of the Database Approach; Actors on the Scene; Workers behind
the Scene; Advantages of Using the DBMS Approach

Unit 2: Database System - Concepts and Architecture (3 Hrs.)
Data Models, Schemas, and Instances; Three-Schema Architecture and Data Independence;
Database Languages and Interfaces; the Database System Environment; Centralized and
Client/Server Architectures for DBMSS; Classification of Database Management Systems

Unit 3: Data Modeling Using the Entity-Relational Model (6 Hrs.)
Using High-Level Conceptual Data Models for Database Design; Entity Types, Entity Sets,
Attributes, and Keys; Relationship Types, Relationship Sets, Roles, and Structural Constraints;
Weak Entity Types; ER Diagrams, Naming Conventions, and Design Issues; Relationship Types
of Degree Higher Than Two; Subclasses, Superclasses, and Inheritance; Specialization and
Generalization; Constraints and Characteristics of Specialization and Generalization

Unit 4: The Relational Data Model and Relational Database Constraints (3 Hrs.)
Relational Model Concepts; Relational Model Constraints and Relational Database Schemas;
Update Operations, Transactions, and Dealing with Constraint Violations

Unit 5: The Relational Algebra and Relational Calculus (5 Hrs.)
Unary Relational Operations: SELECT and PROJECT; Relational Algebra Operations from Set
Theory; Binary Relational Operations: JOIN and DIVISION; Additional Relational Operations;
the Tuple Relational Calculus; the Domain Relational Calculus

Unit 6: SQL (8 Hrs.)
Data Definition and Data Types; Specifying Constraints; Basic Retrieval Queries; Complex
Retrieval Queries; INSERT, DELETE, and UPDATE Statements; Views

45


--- PAGE 11 ---

Unit 7: Relational Database Design (7 Hrs.)
Relational Database Design Using ER-to-Relational Mapping; Informal Design Guidelines for
Relational Schemas; Functional Dependencies; Normal Forms Based on Primary Keys; General
Definitions of Second and Third Normal Forms; Boyce-Codd Normal Form; Multivalued
Dependency and Fourth Normal Form; Properties of Relational Decomposition

Unit 8: Introduction to Transaction Processing Concepts and Theory (4 Hrs.)
Introduction to Transaction Processing; Transaction and System Concepts; Desirable Properties
of Transactions; Characterizing Schedules Based on Recoverability; Characterizing Schedules
Based on Serializability

Unit 9: Concurrency Control Techniques (4 Hrs.)
Two-Phase Locking Technique; Timestamp Ordering; Multiversion Concurrency Control;
Validation (Optimistic) Techniques and Snapshot Isolation Concurrency Control

Unit 10: Database Recovery Techniques (3 Hrs.)
Recovery Concepts; NO-UNDO/REDO Recovery Based on Deferred Update; Recovery
Technique Based on Immediate Update; Shadow Paging; Database Backup and Recovery from
Catastrophic Failures

Laboratory Works:
The laboratory work includes writing database programs to create and query databases using
basic and advanced features of structured query language (SQL).

Text Books:
1. Fundamentals of Database Systems; Seventh Edition; Ramez Elmasri, Shamkant B. Navathe;
Pearson Education
2. Database System Concepts; Sixth Edition; Avi Silberschatz, Henry F Korth, S Sudarshan;
McGraw-Hill

Reference Books:
1. Database Management Systems; Third Edition; Raghu Ramakrishnan, Johannes Gehrke;
McGraw-Hill
2. A First Course in Database Systems; Jaffrey D. Ullman, Jennifer Widom; Third Edition;
Pearson Education Limited

46


--- PAGE 12 ---

Course Title: Artificial Intelligence
Course No: CSC261
Nature of the Course: Theory + Lab
Semester: IV
Full Marks: $60+20+20$
Pass Marks: $24+8+8$
Credit Hrs: 3

Course Description: The course introduces the ideas and techniques underlying the principles
and design of artificial intelligent systems. The course covers the basics and applications of AI,
including: design of intelligent agents, problem solving, searching, knowledge representation
systems, probabilistic reasoning, neural networks, machine learning and natural language
processing.

Course Objectives: The main objective of the course is to introduce fundamental concepts of
Artificial Intelligence. The general objectives are to learn about computer systems that exhibit
intelligent behavior, design intelligent agents, identify Al problems and solve the problems,
design knowledge representation and expert systems, design neural networks for solving
problems, identify different machine learning paradigms and identify their practical applications.

Course Contents:

Unit I: Introduction (3 Hrs.)
1.1. Artificial Intelligence (AI), AI Perspectives: acting and thinking humanly, acting and
thinking rationally
1.2. History of AI
1.3. Foundations of AI
1.4. Applications of Al

Unit II: Intelligent Agents (4 Hrs.)
2.1. Introduction of agents, Structure of Intelligent agent, Properties of Intelligent Agents
2.2. Configuration of Agents, PEAS description of Agents
2.3. Types of Agents: Simple Reflexive, Model Based, Goal Based, Utility Based.
2.4. Environment Types: Deterministic, Stochastic, Static, Dynamic, Observable, Semi-
observable, Single Agent, Multi Agent

Unit III: Problem Solving by Searching (9 Hrs.)
3.1. Definition, Problem as a state space search, Problem formulation, Well-defined
problems,
3.2. Solving Problems by Searching, Search Strategies, Performance evaluation of search
techniques
3.3. Uninformed Search: Depth First Search, Breadth First Search, Depth Limited Search,
Iterative Deepening Search, Bidirectional Search
3.4. Informed Search: Greedy Best first search, $A^{*}$ search, Hill Climbing, Simulated
Annealing
3.5. Game playing, Adversarial search techniques, Mini-max Search, Alpha-Beta Pruning.
3.6. Constraint Satisfaction Problems

47


--- PAGE 13 ---

Unit IV: Knowledge Representation (14 Hrs.)
4.1. Definition and importance of Knowledge, Issues in Knowledge Representation,
Knowledge Representation Systems, Properties of Knowledge Representation Systems.
4.2. Types of Knowledge Representation Systems: Semantic Nets, Frames, Conceptual
Dependencies, Scripts, Rule Based Systems, Propositional Logic, Predicate Logic
4.3. Propositional Logic(PL): Syntax, Semantics, Formal logic-connectives, truth tables,
tautology, validity, well-formed-formula, Inference using Resolution, Backward
Chaining and Forward Chaining
4.4. Predicate Logic: FOPL, Syntax, Semantics, Quantification, Inference with FOPL: By
converting into PL (Existential and universal instantiation), Unification and lifting,
Inference using resolution
4.5. Handling Uncertain Knowledge, Radom Variables, Prior and Posterior Probability,
Inference using Full Joint Distribution, Bayes' Rule and its use, Bayesian Networks,
Reasoning in Belief Networks
4.6. Fuzzy Logic

Unit V: Machine Learning (9 Hrs.)
5.1. Introduction to Machine Learning, Concepts of Learning, Supervised, Unsupervised and
Reinforcement Learning
5.2. Statistical-based Learning: Naive Bayes Model
5.3. Learning by Genetic Algorithm
5.4. Learning with Neural Networks: Introduction, Biological Neural Networks Vs. Artificial
Neural Networks (ANN), Mathematical Model of ANN, Types of ANN: Feed-forward,
Recurrent, Single Layered, Multi-Layered, Application of Artificial Neural Networks,
Learning by Training ANN, Supervised vs. Unsupervised Learning, Hebbian Learning,
Perceptron Learning, Back-propagation Learning

Unit VI: Applications of AI (6 Hrs.)
6.1. Expert Systems, Development of Expert Systems
6.2. Natural Language Processing: Natural Language Understanding and Natural Language
Generation, Steps of Natural Language Processing
6.3. Machine Vision Concepts
6.4. Robotics

Laboratory Works:
The laboratory work consists of design and implementation of intelligent agents and expert
systems, searching techniques, knowledge representation systems and machine learning
techniques. Students are also advised to implement Neural Networks, Genetic Algorithms for
solving practical problems of AI. Students are advised to use LISP, PROLOG, or any other high
level language.

Text Books:
1. Stuart Russel and Peter Norvig, Artificial Intelligence A Modern Approach, Pearson

48


--- PAGE 14 ---

Reference Books:
1. E. Rich, K. Knight, Shivashankar B. Nair, Artificial Intelligence, Tata McGraw Hill.
2. George F. Luger, Artificial Intelligence: Structures and Strategies for Complex Problem
Solving, Benjamin/Cummings Publication
3. D. W. Patterson, Artificial Intelligence and Expert Systems, Prentice Hall.
4. P. H. Winston, Artificial Intelligence, Addison Wesley.

49
"""


# --- Task Data Model (using QAbstractTableModel) ---
class TaskTableModel(QAbstractTableModel):
    def __init__(self, data, headers, parent=None):
        super().__init__(parent)
        self._data = data  # List of dictionaries
        self.headers = headers

    def rowCount(self, parent=QModelIndex()):
        return len(self._data)

    def columnCount(self, parent=QModelIndex()):
        return len(self.headers)

    def data(self, index, role=Qt.DisplayRole) -> QVariant:  # Explicitly type hint QVariant
        if not index.isValid():
            return QVariant()  # Return default-constructed (invalid) QVariant

        row = index.row()
        if not (0 <= row < len(self._data)):
            return QVariant()

        col_key = self.headers[index.column()]
        value = self._data[row].get(col_key)

        if role == Qt.DisplayRole:
            if isinstance(value, datetime.date):
                return QVariant(value.strftime("%Y-%m-%d"))
            elif isinstance(value, datetime.datetime):
                return QVariant(value.strftime("%Y-%m-%d %H:%M:%S"))
            elif value is None:
                return QVariant("")  # Represent None as empty string for display
            else:
                return QVariant(str(value))  # Convert other types to string for display
        elif role == Qt.EditRole:
            if isinstance(value, datetime.date):
                # For QDateEdit, it expects QDate
                return QDate(value.year, value.month, value.day)
            # For other types, QVariant can wrap them directly for editing
            # if the default delegate supports it.
            return QVariant(value)  # Wrap the raw value

        return QVariant()  # Default for other roles

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role == Qt.DisplayRole and orientation == Qt.Horizontal:
            return QVariant(self.headers[section])  # Wrap header string in QVariant
        return QVariant()

    def flags(self, index):
        if not index.isValid():
            return Qt.NoItemFlags
        return Qt.ItemIsSelectable | Qt.ItemIsEnabled | Qt.ItemIsEditable

    def setData(self, index, value, role=Qt.EditRole):
        if not index.isValid() or role != Qt.EditRole:
            return False

        row = index.row()
        if not (0 <= row < len(self._data)):
            return False

        col_key = self.headers[index.column()]

        # The 'value' from QTableView's editor (e.g., QDateEdit) might be QDate
        if isinstance(value, QDate):
            py_value = value.toPyDate()
        elif isinstance(value, QVariant):  # QVariant might wrap the value
            py_value = value.value()  # Unwrap QVariant
            if isinstance(py_value, QDate):  # If QVariant contained QDate
                py_value = py_value.toPyDate()
        else:
            py_value = value  # Assume it's already a Python type or string

        self._data[row][col_key] = py_value
        self.dataChanged.emit(index, index, [role])
        return True

    def insertRows(self, position, rows=1, parent=QModelIndex()):
        position = max(0, min(position, self.rowCount()))
        self.beginInsertRows(parent, position, position + rows - 1)
        for i in range(rows):
            default_task = {key: None for key in self.headers}
            default_task['Status'] = 'Pending'
            default_task['Timestamp'] = datetime.datetime.now()
            default_task['Assigned'] = datetime.date.today()
            default_task['Submit By'] = datetime.date.today() + datetime.timedelta(days=7)
            self._data.insert(position + i, default_task)
        self.endInsertRows()
        return True

    def removeRows(self, position, rows=1, parent=QModelIndex()):
        if position < 0 or position + rows > len(self._data):
            return False
        self.beginRemoveRows(parent, position, position + rows - 1)
        for _ in range(rows):  # Use _ if loop variable i is not used
            if position < len(self._data):
                del self._data[position]
            else:
                break
        self.endRemoveRows()
        return True

    def get_data(self):
        return self._data

    def get_row_data(self, row_index):
        if 0 <= row_index < len(self._data):
            return self._data[row_index]
        return None


# --- Main Application Window ---
class SyllabusTrackerApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Syllabus & Task Tracker (PyQt5)")
        self.setGeometry(100, 100, 1200, 700)

        self.central_widget = None
        self.main_layout = None
        self.notice_board_label = None
        self.tabs = None
        self.footer_label = None
        self.syllabus_tab = None
        self.subject_list_widget = None  # Initialized in create_syllabus_tab
        self.ongoing_chapter_combo = None
        self.ongoing_status_label = None
        self.subject_title_label = None
        self.ongoing_display_label = None
        self.course_info_layout = None
        self.course_no_label = None
        self.credit_hrs_label = None
        self.semester_label = None
        self.full_marks_label = None
        self.pass_marks_label = None
        self.units_display = None
        self.lab_display = None
        self.task_tab = None
        self.task_subject_combo = None
        self.task_type_combo = None
        self.task_desc_edit = None
        self.task_assigned_date = None
        self.task_submit_date = None
        self.task_status_combo = None
        self.add_task_button = None
        self.update_task_button = None
        self.clear_form_button = None
        self.delete_task_button = None
        self.task_table_view = None
        self.task_table_model = None
        self.task_headers = ["Subject", "Type", "Description", "Assigned", "Submit By", "Status",
                             "Timestamp"]  # Added Timestamp for sorting

        self.syllabus_data = parse_syllabus(pdf_text)
        self.subjects = sorted(list(self.syllabus_data.keys()))
        self.tasks = self._load_tasks()
        self.ongoing_chapters = self._load_ongoing_chapters()

        self.setup_ui()

        if self.subjects and self.subject_list_widget:  # Ensure widget exists
            if self.subject_list_widget.count() > 0:  # Check if list has items
                self.subject_list_widget.setCurrentRow(0)  # Triggers on_subject_selected
            elif self.subjects:  # If list is empty but subjects exist, display first one
                self.display_subject_details(self.subjects[0])
        elif not self.subjects:  # No subjects parsed
            self.subject_title_label.setText("No subjects found in syllabus data.")
            self.units_display.setText("Please check the syllabus text format.")

        self.update_notice_board()

    def setup_ui(self):
        self.central_widget = QWidget()
        self.main_layout = QVBoxLayout(self.central_widget)
        self.setCentralWidget(self.central_widget)

        self.notice_board_label = QLabel("Recent Task Updates:")
        self.notice_board_label.setFont(QFont("Arial", 10, QFont.Bold))
        self.main_layout.addWidget(self.notice_board_label)

        self.tabs = QTabWidget()
        self.main_layout.addWidget(self.tabs)

        self.create_syllabus_tab()
        self.create_task_manager_tab()

        self.footer_label = QLabel(f"Designed and Developed By Aadarsha Jha © {datetime.date.today().year}")
        self.footer_label.setAlignment(Qt.AlignCenter)
        self.footer_label.setStyleSheet("color: gray; font-size: 9pt;")
        self.main_layout.addWidget(self.footer_label)

    def create_syllabus_tab(self):
        self.syllabus_tab = QWidget()
        self.tabs.addTab(self.syllabus_tab, "📝 Syllabus & Chapters")
        syllabus_layout = QHBoxLayout(self.syllabus_tab)
        splitter = QSplitter(Qt.Horizontal)
        syllabus_layout.addWidget(splitter)

        left_pane = QWidget()
        left_layout = QVBoxLayout(left_pane)
        left_pane.setMaximumWidth(300)

        subject_group = QGroupBox("Select Subject")
        subject_layout_inner = QVBoxLayout(subject_group)  # Renamed to avoid conflict
        self.subject_list_widget = QListWidget()
        self.subject_list_widget.addItems(self.subjects)
        self.subject_list_widget.currentItemChanged.connect(self.on_subject_selected)
        subject_layout_inner.addWidget(self.subject_list_widget)
        left_layout.addWidget(subject_group)

        ongoing_group = QGroupBox("Ongoing Chapter")
        ongoing_layout = QVBoxLayout(ongoing_group)
        self.ongoing_chapter_combo = QComboBox()
        self.ongoing_chapter_combo.addItem("-- Select Ongoing Chapter --")
        self.ongoing_chapter_combo.currentTextChanged.connect(self.on_ongoing_chapter_changed)
        ongoing_layout.addWidget(self.ongoing_chapter_combo)
        self.ongoing_status_label = QLabel("(Not Set)")
        ongoing_layout.addWidget(self.ongoing_status_label)
        left_layout.addWidget(ongoing_group)
        left_layout.addStretch()

        right_pane = QWidget()
        right_layout = QVBoxLayout(right_pane)
        self.subject_title_label = QLabel("Select a subject")
        self.subject_title_label.setFont(QFont("Arial", 14, QFont.Bold))
        right_layout.addWidget(self.subject_title_label)
        self.ongoing_display_label = QLabel("")
        self.ongoing_display_label.setStyleSheet("color: green; font-weight: bold;")
        self.ongoing_display_label.setVisible(False)
        right_layout.addWidget(self.ongoing_display_label)

        course_info_group = QGroupBox("Course Information")
        self.course_info_layout = QFormLayout(course_info_group)
        self.course_no_label = QLabel("N/A")
        self.credit_hrs_label = QLabel("N/A")
        self.semester_label = QLabel("N/A")
        self.full_marks_label = QLabel("N/A")
        self.pass_marks_label = QLabel("N/A")
        self.course_info_layout.addRow("Course No:", self.course_no_label)
        self.course_info_layout.addRow("Credit Hrs:", self.credit_hrs_label)
        self.course_info_layout.addRow("Semester:", self.semester_label)
        self.course_info_layout.addRow("Full Marks:", self.full_marks_label)
        self.course_info_layout.addRow("Pass Marks:", self.pass_marks_label)
        right_layout.addWidget(course_info_group)

        units_group = QGroupBox("Course Units")
        units_layout = QVBoxLayout(units_group)
        self.units_display = QTextEdit()
        self.units_display.setReadOnly(True)
        units_layout.addWidget(self.units_display)
        right_layout.addWidget(units_group)

        lab_group = QGroupBox("Laboratory Works")
        lab_layout = QVBoxLayout(lab_group)
        self.lab_display = QTextEdit()
        self.lab_display.setReadOnly(True)
        lab_layout.addWidget(self.lab_display)
        right_layout.addWidget(lab_group)

        splitter.addWidget(left_pane)
        splitter.addWidget(right_pane)
        splitter.setSizes([250, 950])

    def create_task_manager_tab(self):
        self.task_tab = QWidget()
        self.tabs.addTab(self.task_tab, "✅ Task Management")
        task_layout = QHBoxLayout(self.task_tab)

        add_task_group = QGroupBox("Add/Edit Task")
        add_task_group.setMaximumWidth(350)
        form_layout = QFormLayout(add_task_group)

        self.task_subject_combo = QComboBox()
        self.task_subject_combo.addItems(
            ["-- Select Subject --"] + self.subjects if self.subjects else ["-- No Subjects --"])
        self.task_type_combo = QComboBox()
        self.task_type_combo.addItems(["Assignment", "Lab Report", "Project", "Presentation", "Study Task"])
        self.task_desc_edit = QLineEdit()

        self.task_assigned_date = QDateEdit()
        self.task_assigned_date.setCalendarPopup(True)  # Set property after instantiation
        self.task_assigned_date.setDate(QDate.currentDate())

        self.task_submit_date = QDateEdit()
        self.task_submit_date.setCalendarPopup(True)  # Set property after instantiation
        self.task_submit_date.setDate(QDate.currentDate().addDays(7))

        self.task_status_combo = QComboBox()
        self.task_status_combo.addItems(["Pending", "In Progress", "Completed", "Cancelled"])

        form_layout.addRow("Subject:", self.task_subject_combo)
        form_layout.addRow("Type:", self.task_type_combo)
        form_layout.addRow("Description:", self.task_desc_edit)
        form_layout.addRow("Date Assigned:", self.task_assigned_date)
        form_layout.addRow("Submit By:", self.task_submit_date)
        form_layout.addRow("Status:", self.task_status_combo)

        button_layout = QHBoxLayout()
        self.add_task_button = QPushButton("➕ Add Task")
        self.update_task_button = QPushButton("💾 Update Selected")
        self.clear_form_button = QPushButton("🧹 Clear Form")

        self.add_task_button.clicked.connect(self.add_task)
        self.update_task_button.clicked.connect(self.update_task)
        self.clear_form_button.clicked.connect(self.clear_task_form)

        button_layout.addWidget(self.add_task_button)
        button_layout.addWidget(self.update_task_button)
        button_layout.addWidget(self.clear_form_button)
        form_layout.addRow(button_layout)

        self.delete_task_button = QPushButton("❌ Delete Selected")
        self.delete_task_button.clicked.connect(self.delete_task)
        form_layout.addRow(self.delete_task_button)

        task_list_group = QGroupBox("Current Tasks List")
        table_layout = QVBoxLayout(task_list_group)
        self.task_table_model = TaskTableModel(self.tasks, self.task_headers)
        self.task_table_view = QTableView()
        self.task_table_view.setModel(self.task_table_model)
        self.task_table_view.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        # Allow Description to be wider and interactive
        try:  # Handle case where "Description" might not be in headers (defensive)
            desc_col_index = self.task_headers.index("Description")
            self.task_table_view.horizontalHeader().setSectionResizeMode(desc_col_index, QHeaderView.Interactive)
            self.task_table_view.setColumnWidth(desc_col_index, 250)  # Give Description more initial space
        except ValueError:
            pass  # "Description" not in headers

        self.task_table_view.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.task_table_view.setSelectionMode(QAbstractItemView.SingleSelection)
        self.task_table_view.setSortingEnabled(True)
        self.task_table_view.selectionModel().selectionChanged.connect(self.on_task_selected)
        table_layout.addWidget(self.task_table_view)

        task_layout.addWidget(add_task_group)
        task_layout.addWidget(task_list_group)

    def on_subject_selected(self):
        selected_item = self.subject_list_widget.currentItem()
        if selected_item:
            subject_name = selected_item.text()
            self.display_subject_details(subject_name)

    def display_subject_details(self, subject_name):
        if subject_name in self.syllabus_data:
            data = self.syllabus_data[subject_name]
            self.subject_title_label.setText(subject_name)
            details = data.get("Details", {})
            self.course_no_label.setText(details.get("Course No", "N/A"))
            self.credit_hrs_label.setText(details.get("Credit Hrs", "N/A"))
            self.semester_label.setText(details.get("Semester", "N/A"))
            self.full_marks_label.setText(details.get("Full Marks", "N/A"))
            self.pass_marks_label.setText(details.get("Pass Marks", "N/A"))

            units_text = "\n\n---\n\n".join(data.get("Units", ["No units found."]))
            self.units_display.setPlainText(units_text)
            self.lab_display.setPlainText(data.get("Lab Work", "No lab work details found."))

            self.ongoing_chapter_combo.blockSignals(True)
            self.ongoing_chapter_combo.clear()
            unit_titles = self._get_unit_titles_for_subject(data)  # Now static
            self.ongoing_chapter_combo.addItems(unit_titles)
            current_ongoing = self.ongoing_chapters.get(subject_name, "-- Select Ongoing Chapter --")
            index = self.ongoing_chapter_combo.findText(current_ongoing)
            self.ongoing_chapter_combo.setCurrentIndex(index if index != -1 else 0)
            self.ongoing_chapter_combo.blockSignals(False)
            self._update_ongoing_status_labels(subject_name)
        else:
            self.subject_title_label.setText(f"Details for '{subject_name}' not found.")
            self.units_display.clear()
            self.lab_display.clear()
            for label in [self.course_no_label, self.credit_hrs_label, self.semester_label, self.full_marks_label,
                          self.pass_marks_label]:
                label.setText("N/A")
            self.ongoing_chapter_combo.clear()
            self.ongoing_chapter_combo.addItem("-- Select Subject First --")
            self._update_ongoing_status_labels(None)

    @staticmethod
    def _get_unit_titles_for_subject(subject_data):
        titles = ["-- Select Ongoing Chapter --"]
        units = subject_data.get("Units")
        if units:
            unit_titles_list = [
                unit_content.splitlines()[0].strip() if unit_content.splitlines() else f"Unit {idx + 1}"
                for idx, unit_content in enumerate(units)
            ]
            titles.extend(unit_titles_list)
        else:  # No units explicitly found under "Units" key
            titles.append("(No Units Found)")
        return titles

    def on_ongoing_chapter_changed(self, selected_text):
        if not self.subject_list_widget or not self.subject_list_widget.currentItem():
            return
        subject_name = self.subject_list_widget.currentItem().text()
        needs_save = False
        if selected_text and selected_text not in ["-- Select Ongoing Chapter --", "(No Units Found)"]:
            if self.ongoing_chapters.get(subject_name) != selected_text:
                self.ongoing_chapters[subject_name] = selected_text
                needs_save = True
        elif subject_name in self.ongoing_chapters:  # Unset if placeholder is selected
            del self.ongoing_chapters[subject_name]
            needs_save = True

        if needs_save:
            self._save_ongoing_chapters()
        self._update_ongoing_status_labels(subject_name)

    def _update_ongoing_status_labels(self, subject_name):
        current_ongoing = self.ongoing_chapters.get(subject_name) if subject_name else None
        if current_ongoing:
            status_text = f"Studying: {current_ongoing}"
            self.ongoing_status_label.setText(status_text)
            self.ongoing_display_label.setText(f"Currently Studying: {current_ongoing}")
            self.ongoing_display_label.setVisible(True)
        else:
            self.ongoing_status_label.setText("(Not Set)")
            self.ongoing_display_label.setText("")
            self.ongoing_display_label.setVisible(False)

    def on_task_selected(self, _selected, _deselected):
        indexes = self.task_table_view.selectionModel().selectedRows()
        if not indexes:
            self.clear_task_form()  # Clear form if selection is cleared
            return

        model_row_index = indexes[0].row()
        task_data = self.task_table_model.get_row_data(model_row_index)

        if task_data:
            self.task_subject_combo.setCurrentText(task_data.get("Subject", ""))
            self.task_type_combo.setCurrentText(task_data.get("Type", "Assignment"))
            self.task_desc_edit.setText(task_data.get("Description", ""))

            assigned_date = task_data.get("Assigned")
            if isinstance(assigned_date, datetime.date):
                self.task_assigned_date.setDate(QDate(assigned_date))
            else:
                self.task_assigned_date.setDate(QDate.currentDate())

            submit_date = task_data.get("Submit By")
            if isinstance(submit_date, datetime.date):
                self.task_submit_date.setDate(QDate(submit_date))
            else:
                self.task_submit_date.setDate(QDate.currentDate().addDays(7))

            self.task_status_combo.setCurrentText(task_data.get("Status", "Pending"))
        else:
            self.clear_task_form()

    def _get_task_data_from_form(self):
        """Retrieves and validates task data from the form."""
        desc = self.task_desc_edit.text().strip()
        if not desc:
            QMessageBox.warning(self, "Input Error", "Task description cannot be empty.")
            return None

        subject = self.task_subject_combo.currentText()
        if subject == "-- Select Subject --" or subject == "-- No Subjects --":
            QMessageBox.warning(self, "Input Error", "Please select a valid subject for the task.")
            return None

        assigned = self.task_assigned_date.date().toPyDate()
        submit = self.task_submit_date.date().toPyDate()
        if assigned > submit:
            QMessageBox.warning(self, "Input Error", "Submission date cannot be before assigned date.")
            return None

        return {
            "Subject": subject,
            "Type": self.task_type_combo.currentText(),
            "Description": desc,
            "Assigned": assigned,
            "Submit By": submit,
            "Status": self.task_status_combo.currentText(),
        }

    def add_task(self):
        task_data = self._get_task_data_from_form()
        if not task_data:
            return

        task_data["Timestamp"] = datetime.datetime.now()

        row_to_insert_at = 0  # Insert at the top
        self.task_table_model.insertRows(row_to_insert_at, 1)
        for col_idx, header in enumerate(self.task_headers):
            index = self.task_table_model.index(row_to_insert_at, col_idx)
            value_to_set = task_data.get(header)
            # setData expects QDate for date fields if editor is QDateEdit
            if header in ["Assigned", "Submit By"] and isinstance(value_to_set, datetime.date):
                value_to_set = QDate(value_to_set)
            self.task_table_model.setData(index, value_to_set, Qt.EditRole)

        # After adding, re-sort if sorting is enabled to maintain order (e.g., by Timestamp)
        # Or, if always adding to top, ensure model._data is updated correctly and view reflects.
        # The current insertRows and setData should place it at row 0 in the model's internal list.

        QMessageBox.information(self, "Success", "Task added successfully.")
        self.clear_task_form()
        self.update_notice_board()
        self._save_tasks()

    def update_task(self):
        selected_indexes = self.task_table_view.selectionModel().selectedRows()
        if not selected_indexes:
            QMessageBox.warning(self, "Selection Error", "Please select a task to update.")
            return

        model_row_index = selected_indexes[0].row()
        if not (0 <= model_row_index < self.task_table_model.rowCount()):
            QMessageBox.critical(self, "Error", "Selected row index is invalid.")
            return

        task_data_from_form = self._get_task_data_from_form()
        if not task_data_from_form:
            return

        # Get original timestamp if it exists, otherwise set new one
        original_task = self.task_table_model.get_row_data(model_row_index)
        task_data_from_form["Timestamp"] = original_task.get("Timestamp", datetime.datetime.now())

        for col_idx, header in enumerate(self.task_headers):
            if header in task_data_from_form:  # Only update headers present in form data + timestamp
                index = self.task_table_model.index(model_row_index, col_idx)
                value_to_set = task_data_from_form[header]
                if header in ["Assigned", "Submit By"] and isinstance(value_to_set, datetime.date):
                    value_to_set = QDate(value_to_set)  # Convert to QDate for model
                self.task_table_model.setData(index, value_to_set, Qt.EditRole)

        QMessageBox.information(self, "Success", "Task updated successfully.")
        self.update_notice_board()
        self._save_tasks()

    def delete_task(self):
        selected_indexes = self.task_table_view.selectionModel().selectedRows()
        if not selected_indexes:
            QMessageBox.warning(self, "Selection Error", "Please select a task to delete.")
            return

        reply = QMessageBox.question(self, "Confirm Delete",
                                     "Are you sure you want to delete the selected task?",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            model_row_index = selected_indexes[0].row()
            if 0 <= model_row_index < self.task_table_model.rowCount():
                self.task_table_model.removeRows(model_row_index, 1)
                QMessageBox.information(self, "Success", "Task deleted successfully.")
                self.clear_task_form()
                self.update_notice_board()
                self._save_tasks()
            else:
                QMessageBox.critical(self, "Error", "Selected row index became invalid.")

    def clear_task_form(self):
        self.task_subject_combo.setCurrentIndex(0)
        self.task_type_combo.setCurrentIndex(0)
        self.task_desc_edit.clear()
        self.task_assigned_date.setDate(QDate.currentDate())
        self.task_submit_date.setDate(QDate.currentDate().addDays(7))
        self.task_status_combo.setCurrentIndex(0)
        self.task_table_view.clearSelection()

    def update_notice_board(self):
        # Sort tasks by Timestamp (datetime object) descending for "Recent"
        # Ensure Timestamp is part of the task data and is a datetime object for proper sorting
        all_tasks = self.task_table_model.get_data()

        # Filter out tasks that might have a None timestamp or invalid one before sorting
        valid_tasks_for_sorting = [task for task in all_tasks if isinstance(task.get('Timestamp'), datetime.datetime)]
        invalid_tasks = [task for task in all_tasks if not isinstance(task.get('Timestamp'), datetime.datetime)]

        # Sort valid tasks
        current_tasks_sorted = sorted(
            valid_tasks_for_sorting,
            key=lambda x: x['Timestamp'],
            reverse=True
        )
        # Add tasks with invalid/missing timestamps at the end or handle as per logic
        current_tasks_sorted.extend(invalid_tasks)

        notice_text = "<b>Recent Task Updates:</b><br>"
        if not current_tasks_sorted:
            notice_text += "(No tasks added yet)"
        else:
            for i, task in enumerate(current_tasks_sorted[:3]):  # Show top 3
                due_date = task.get('Submit By')
                urgency_color = "green"
                urgency_text = ""
                if isinstance(due_date, datetime.date):
                    due_date_str = due_date.strftime('%Y-%m-%d')
                    days_left = (due_date - datetime.date.today()).days
                    if days_left < 0:
                        urgency_text = f"Past Due by {-days_left} day(s)"
                        urgency_color = "red"
                    elif days_left == 0:
                        urgency_text = "Due Today!"
                        urgency_color = "orange"
                    elif days_left <= 3:
                        urgency_text = f"Due in {days_left} day(s)"
                        urgency_color = "darkorange"
                    else:
                        urgency_text = f"Due in {days_left} days"
                else:
                    due_date_str = str(due_date if due_date is not None else 'N/A')

                notice_text += f"- {task.get('Type', 'Task')} ({task.get('Subject', 'N/A')}): {task.get('Description', 'No desc.')} " \
                               f"[Due: {due_date_str} <font color='{urgency_color}'>{urgency_text}</font>]<br>"
        self.notice_board_label.setText(notice_text.strip())

    @staticmethod
    def _get_tasks_filepath():
        return "syllabus_tasks.json"

    @staticmethod
    def _get_ongoing_chapters_filepath():
        return "ongoing_chapters.json"

    def _load_tasks(self):
        filepath = self._get_tasks_filepath()
        try:
            with open(filepath, 'r') as f:
                tasks_data = json.load(f)
                for task in tasks_data:
                    for key in ["Assigned", "Submit By"]:
                        if key in task and isinstance(task[key], str):
                            try:
                                task[key] = datetime.datetime.strptime(task[key], "%Y-%m-%d").date()
                            except ValueError:
                                task[key] = None
                    if 'Timestamp' in task and isinstance(task['Timestamp'], str):
                        try:
                            task['Timestamp'] = datetime.datetime.fromisoformat(
                                task['Timestamp'].replace('Z', '+00:00'))
                        except ValueError:
                            task['Timestamp'] = datetime.datetime.min  # Default for sorting if invalid
                # Sort by timestamp after loading and conversion
                tasks_data.sort(key=lambda x: x.get('Timestamp', datetime.datetime.min), reverse=True)
                return tasks_data
        except FileNotFoundError:
            return []
        except (json.JSONDecodeError, Exception) as e:
            print(f"Error loading tasks: {e}")
            QMessageBox.warning(self, "Load Error",
                                f"Could not load tasks from {filepath}.\nError: {e}\nStarting with an empty list.")
            return []

    def _save_tasks(self):
        filepath = self._get_tasks_filepath()
        try:
            tasks_to_save = self.task_table_model.get_data()
            with open(filepath, 'w') as f:
                def json_serializer(obj):
                    if isinstance(obj, (datetime.date, datetime.datetime)):
                        return obj.isoformat()
                    raise TypeError(f"Type {type(obj)} not serializable for JSON: {obj}")

                json.dump(tasks_to_save, f, indent=4, default=json_serializer)
        except Exception as e:
            print(f"Error saving tasks: {e}")
            QMessageBox.critical(self, "Save Error", f"Could not save tasks to {filepath}.\nError: {e}")

    def _load_ongoing_chapters(self):
        filepath = self._get_ongoing_chapters_filepath()
        try:
            with open(filepath, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return {}
        except (json.JSONDecodeError, Exception) as e:
            print(f"Error loading ongoing chapters: {e}")
            QMessageBox.warning(self, "Load Error", f"Could not load ongoing chapters: {e}")
            return {}

    def _save_ongoing_chapters(self):
        filepath = self._get_ongoing_chapters_filepath()
        try:
            with open(filepath, 'w') as f:
                json.dump(self.ongoing_chapters, f, indent=4)
        except Exception as e:
            print(f"Error saving ongoing chapters: {e}")
            QMessageBox.critical(self, "Save Error", f"Could not save ongoing chapters: {e}")

    def closeEvent(self, event):
        self._save_tasks()
        self._save_ongoing_chapters()
        super().closeEvent(event)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")  # Optional: Apply a style
    main_window = SyllabusTrackerApp()
    main_window.show()
    sys.exit(app.exec_())