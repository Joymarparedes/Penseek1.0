#!/usr/bin/env python3
import sqlite3
import json
import os
import curses
import textwrap
import random
from datetime import datetime

# Define data folder and file paths
DATA_FOLDER = os.path.expanduser("~/penseek_1.0/penseek_data/")
SPLASH_FILE = os.path.join(DATA_FOLDER, "splash.ans")

# Hacker quotes for splash screen
HACKER_QUOTES = [
    "Hack the planet!",
    "Access granted...",
    "Exploit found. Deploying payload...",
    "Data wants to be free.",
    "01100110 01101001 01101110 01100100 00100000 01101111 01110101 01110100",
]

class PenseekDB:
    def __init__(self):
        """Initialize the database and create the table if it doesn't exist."""
        os.makedirs(DATA_FOLDER, exist_ok=True)
        self.db_path = os.path.join(DATA_FOLDER, "penseek.db")
        self.conn = sqlite3.connect(self.db_path)
        self._init_db()

    def _init_db(self):
        """Create the CVE table if it doesn't exist."""
        self.conn.execute('''
            CREATE TABLE IF NOT EXISTS cves (
                id TEXT PRIMARY KEY,
                description TEXT,
                severity TEXT,
                published DATE,
                exploit_available BOOLEAN
            )
        ''')
        self.conn.commit()

    def update_from_json(self, json_file):
        """Load CVE data from a JSON file and update the database."""
        try:
            json_path = os.path.join(DATA_FOLDER, json_file)
            with open(json_path, 'r') as file:
                data = json.load(file)

            if "vulnerabilities" not in data:
                print(f"Invalid JSON format: Missing 'vulnerabilities' key in {json_file}.")
                return

            vulnerabilities = data.get("vulnerabilities", [])
            
            new_data = []
            for vuln in vulnerabilities:
                cve_id = vuln.get("cveID", "UNKNOWN")
                description = vuln.get("shortDescription", "No description available.")
                published = vuln.get("dateAdded", "Unknown")
                exploit_available = vuln.get("knownRansomwareCampaignUse", "").lower() != "unknown"
                new_data.append((cve_id, description, "Unknown", published, exploit_available))

            self.conn.executemany('INSERT OR REPLACE INTO cves VALUES (?, ?, ?, ?, ?)', new_data)
            self.conn.commit()
            print("\n╔════════════════════════════════════╗")
            print(f"║  Database updated with {len(new_data)} CVEs  ║")
            print("╚════════════════════════════════════╝")
        except json.JSONDecodeError:
            print("Error: The JSON file is not formatted correctly.")
        except Exception as e:
            print(f"Error updating database: {e}")

    def search(self, query):
        """Search the CVE database."""
        cursor = self.conn.execute(
            'SELECT * FROM cves WHERE id LIKE ? OR description LIKE ?', 
            (f'%{query}%', f'%{query}%')
        )
        results = cursor.fetchall()
        return results

def show_splash_screen(stdscr):
    """Display splash screen and hacker quote."""
    try:
        stdscr.clear()
        height, width = stdscr.getmaxyx()
        if os.path.exists(SPLASH_FILE):
            with open(SPLASH_FILE, 'r', encoding="utf-8", errors="ignore") as f:
                splash_lines = f.readlines()

            max_width = width - 4  # Prevent writing off screen
            processed_lines = [line[:max_width] for line in splash_lines]
            start_row = max(0, (height - len(processed_lines)) // 2)
            for i, line in enumerate(processed_lines):
                col = max(0, (width - len(line)) // 2)
                if start_row + i < height:
                    stdscr.addstr(start_row + i, col, line)
        else:
            stdscr.addstr(height // 2, (width - 40) // 2, "Welcome to Penseek 1.0!", curses.A_BOLD)

        # Display a random hacker quote at the bottom
        quote = random.choice(HACKER_QUOTES)
        stdscr.addstr(height - 3, (width - len(quote)) // 2, quote, curses.A_BOLD)
        stdscr.refresh()
        stdscr.getch()
    except Exception:
        stdscr.clear()
        stdscr.addstr(2, 2, "Welcome to Penseek 1.0 - Your Offline CVE Database!")
        stdscr.refresh()
        stdscr.getch()

def format_search_results(results, width=60):
    """Format the CVE search results with ASCII styling."""
    if not results:
        return [
            "╔════════════════════════════════════╗",
            "║         No results found!          ║",
            "╚════════════════════════════════════╝"
        ]

    output = []
    output.append("╔" + "═" * (width - 2) + "╗")
    output.append(f"║{'CVE Search Results':^{width-2}}║")
    output.append("╠" + "═" * (width - 2) + "╣")

    for cve in results:
        cve_id, desc, severity, published, exploit = cve
        exploit_status = "[EXPLOIT]" if exploit else "[NO EXPLOIT]"
        # Prepare the main line with basic CVE info
        info_line = f"{cve_id}  {severity}  {published}  {exploit_status}"
        output.append(f"║ {info_line.ljust(width-4)} ║")
        # Wrap and add the description
        wrapped_desc = textwrap.wrap(f"Description: {desc}", width=width - 4)
        for line in wrapped_desc:
            output.append(f"║ {line.ljust(width-4)} ║")
        output.append("╠" + "═" * (width - 2) + "╣")

    output.append("╚" + "═" * (width - 2) + "╝")
    return output

def search_cves(stdscr, db):
    curses.echo()
    stdscr.clear()
    stdscr.addstr(2, 2, "Enter search: ")
    stdscr.refresh()
    query = stdscr.getstr(2, 20, 50).decode("utf-8")
    
    results = db.search(query)
    formatted_results = format_search_results(results)
    
    stdscr.clear()
    max_y, max_x = stdscr.getmaxyx()
    start_line = 0
    
    while True:
        stdscr.clear()
        for i in range(min(len(formatted_results) - start_line, max_y - 2)):
            try:
                stdscr.addstr(i + 1, 2, formatted_results[start_line + i])
            except curses.error:
                pass  # Ignore errors for oversized text
        stdscr.refresh()
        
        key = stdscr.getch()
        if key == curses.KEY_DOWN and start_line < len(formatted_results) - (max_y - 2):
            start_line += 1
        elif key == curses.KEY_UP and start_line > 0:
            start_line -= 1
        elif key == curses.KEY_NPAGE and start_line + (max_y - 2) < len(formatted_results):
            start_line += max_y - 2
        elif key == curses.KEY_PPAGE and start_line > 0:
            start_line -= max_y - 2
        elif key in [10, 13, 27]:  # Enter or ESC to exit
            break

def choose_json_file(stdscr, db):
    """Let user choose a JSON file from penseek_data folder."""
    curses.echo()
    stdscr.clear()
    stdscr.addstr(2, 2, "Available JSON files in penseek_data:\n")
    
    json_files = [f for f in os.listdir(DATA_FOLDER) if f.endswith(".json")]
    if not json_files:
        stdscr.addstr(4, 2, "No JSON files found in penseek_data.")
        stdscr.refresh()
        stdscr.getch()
        return

    current_row = 0
    while True:
        stdscr.clear()
        stdscr.addstr(2, 2, "Select a JSON file to update the database:\n")
        for i, file in enumerate(json_files):
            y = 4 + i
            if i == current_row:
                stdscr.attron(curses.A_REVERSE)
                stdscr.addstr(y, 2, file)
                stdscr.attroff(curses.A_REVERSE)
            else:
                stdscr.addstr(y, 2, file)
        stdscr.refresh()

        key = stdscr.getch()
        if key == curses.KEY_UP and current_row > 0:
            current_row -= 1
        elif key == curses.KEY_DOWN and current_row < len(json_files) - 1:
            current_row += 1
        elif key in [10, 13]:  # Enter key
            db.update_from_json(json_files[current_row])
            stdscr.addstr(4 + len(json_files) + 2, 2, "Press any key to continue...")
            stdscr.refresh()
            stdscr.getch()
            break

def draw_menu(stdscr, db):
    curses.curs_set(0)
    stdscr.clear()
    stdscr.refresh()
    height, width = stdscr.getmaxyx()
    
    # Main menu header (ASCII header can be added here if desired)
    menu = ["[1] Search CVEs", "[2] Update Database", "[3] Exit"]
    current_row = 0

    while True:
        stdscr.clear()
        for i, row in enumerate(menu):
            x = width // 2 - len(row) // 2
            y = height // 2 - len(menu) // 2 + i
            if i == current_row:
                stdscr.attron(curses.A_REVERSE)
                stdscr.addstr(y, x, row)
                stdscr.attroff(curses.A_REVERSE)
            else:
                stdscr.addstr(y, x, row)
        stdscr.refresh()
        
        key = stdscr.getch()
        if key == curses.KEY_UP and current_row > 0:
            current_row -= 1
        elif key == curses.KEY_DOWN and current_row < len(menu) - 1:
            current_row += 1
        elif key in [10, 13]:
            if current_row == 0:
                search_cves(stdscr, db)
            elif current_row == 1:
                choose_json_file(stdscr, db)
            elif current_row == 2:
                break

def main(stdscr):
    db = PenseekDB()
    show_splash_screen(stdscr)
    draw_menu(stdscr, db)

if __name__ == "__main__":
    curses.wrapper(main)

