#!/usr/bin/env python3
"""
Supabase Migrations Consolidator

A tool to consolidate Supabase migrations into a single file with options to
backup and delete past migrations, and rename to an init migration.

Features:
- Consolidates all SQL migrations into a single file
- Simple interactive menu
- Option to backup all original migrations
- Option to delete original migrations after backup
- Option to rename consolidated file as an init migration
"""

import os
import re
import sys
import shutil
import datetime
import argparse
from typing import List, Dict, Any

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.prompt import Confirm
    from rich.progress import Progress, SpinnerColumn, TextColumn
    from rich.syntax import Syntax
    from rich.table import Table
    from rich import print as rprint
    from rich.text import Text
    RICH_AVAILABLE = True
except ImportError:
    print("Rich library not found. For a better experience, install it with: pip install rich")
    RICH_AVAILABLE = False

# Configuration
MIGRATIONS_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_FILE = os.path.join(MIGRATIONS_DIR, "consolidated_migration.sql")
TEMP_FILE = os.path.join(MIGRATIONS_DIR, "consolidated_migration.sql.tmp")
BACKUP_FILE = os.path.join(MIGRATIONS_DIR, "consolidated_migration.sql.bak")
BACKUP_DIR = os.path.join(MIGRATIONS_DIR, "backups")

# Initialize Rich console if available
console = Console() if RICH_AVAILABLE else None

def log(message: str, style: str = None) -> None:
    """Print messages with Rich styling if available, otherwise plain print"""
    if RICH_AVAILABLE and console:
        console.print(message, style=style)
    else:
        print(message)

def create_backup_dir() -> None:
    """Create backup directory if it doesn't exist"""
    if not os.path.exists(BACKUP_DIR):
        os.makedirs(BACKUP_DIR)
        log(f"Created backup directory at {BACKUP_DIR}", "green")

def backup_migrations(migration_files: List[str]) -> str:
    """Backup all migration files to a timestamped directory"""
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_subdir = os.path.join(BACKUP_DIR, f"migrations_backup_{timestamp}")
    
    os.makedirs(backup_subdir)
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console if RICH_AVAILABLE else None
    ) as progress:
        task = progress.add_task("[cyan]Backing up migration files...", total=len(migration_files))
        
        for filename in migration_files:
            src_path = os.path.join(MIGRATIONS_DIR, filename)
            dst_path = os.path.join(backup_subdir, filename)
            shutil.copy2(src_path, dst_path)
            progress.update(task, advance=1)
    
    log(f"All migrations backed up to [bold]{backup_subdir}[/bold]", "green")
    return backup_subdir

def delete_migrations(migration_files: List[str]) -> None:
    """Delete all migration files from the migrations directory"""
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console if RICH_AVAILABLE else None
    ) as progress:
        task = progress.add_task("[red]Deleting migration files...", total=len(migration_files))
        
        for filename in migration_files:
            file_path = os.path.join(MIGRATIONS_DIR, filename)
            os.remove(file_path)
            progress.update(task, advance=1)
    
    log("Original migration files have been deleted", "yellow")

def rename_to_init(timestamp: str = None) -> None:
    """Rename consolidated file to an init migration with timestamp"""
    if timestamp is None:
        timestamp = datetime.datetime.now().strftime("%Y%m%d")
    
    init_filename = f"{timestamp}_initial_schema.sql"
    init_file_path = os.path.join(MIGRATIONS_DIR, init_filename)
    
    # If the init file already exists, back it up
    if os.path.exists(init_file_path):
        backup_path = os.path.join(BACKUP_DIR, f"{init_filename}.bak")
        shutil.copy2(init_file_path, backup_path)
        log(f"Existing init file backed up to {backup_path}", "yellow")
        os.remove(init_file_path)
    
    # Rename consolidated file to init file
    shutil.copy2(OUTPUT_FILE, init_file_path)
    log(f"Consolidated file renamed to {init_filename}", "green")

def show_menu() -> Dict[str, Any]:
    """Show a simple cross-platform menu for configuration options"""
    options = {
        "backup": True,  # Default to True for safety
        "delete": False,
        "rename": False,
        "timestamp": datetime.datetime.now().strftime("%Y%m%d")
    }
    
    while True:
        # Clear screen
        os.system('cls' if os.name == 'nt' else 'clear')
        
        print("\n=== Supabase Migrations Consolidator - Configuration ===\n")
        print(f"1. {'[X]' if options['backup'] else '[ ]'} Create backup of original migrations")
        print(f"2. {'[X]' if options['delete'] else '[ ]'} Delete original migrations after backup")
        print(f"3. {'[X]' if options['rename'] else '[ ]'} Rename consolidated file to init migration")
        print("4. Proceed with consolidation")
        print("5. Cancel operation\n")
        
        choice = input("Enter your choice (1-5): ").strip()
        
        if choice == '5':
            sys.exit("Operation cancelled by user")
        elif choice == '4':
            break
        elif choice == '1':
            options["backup"] = not options["backup"]
            if options["delete"] and not options["backup"]:
                options["backup"] = True
                print("\nWarning: Backup must be enabled when delete is enabled")
                input("Press Enter to continue...")
        elif choice == '2':
            options["delete"] = not options["delete"]
            if options["delete"] and not options["backup"]:
                options["backup"] = True
                print("\nWarning: Backup must be enabled when delete is enabled")
                input("Press Enter to continue...")
        elif choice == '3':
            options["rename"] = not options["rename"]
            if options["rename"]:
                timestamp = input(f"\nEnter timestamp for init file (default: {options['timestamp']}): ")
                if timestamp.strip():
                    options["timestamp"] = timestamp.strip()
    
    return options

def consolidate_migrations(options: Dict[str, Any] = None) -> None:
    """Main function to consolidate migrations"""
    if options is None:
        options = {
            "backup": True,
            "delete": False,
            "rename": False,
            "timestamp": datetime.datetime.now().strftime("%Y%m%d")
        }
    
    # Get all migration files (excluding the consolidated file and this script)
    migration_files = [f for f in os.listdir(MIGRATIONS_DIR) 
                    if f.endswith('.sql') and not f.startswith('consolidated_migration')]
    
    # Also exclude the init migration if we plan to create one
    if options["rename"]:
        migration_files = [f for f in migration_files if not f.startswith(f"{options['timestamp']}_initial_schema")]
    
    # Sort files by their timestamp/name to maintain the correct order
    migration_files.sort()
    
    if not migration_files:
        log("No migration files found.", "red")
        return
    
    log(f"Found {len(migration_files)} migration files.", "cyan")
    
    # Create backup directory if needed
    if options["backup"]:
        create_backup_dir()
        backup_dir = backup_migrations(migration_files)
        log(f"Backup complete: {backup_dir}", "green")
    
    # Create the consolidated file (using a temp file first)
    with open(TEMP_FILE, 'w') as outfile:
        # Write header
        outfile.write("-- CONSOLIDATED MIGRATION FILE\n")
        outfile.write(f"-- This file combines all migrations from {migration_files[0]} through {migration_files[-1]}\n")
        outfile.write(f"-- Created on {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        outfile.write("-- Created for easier management while preserving original migrations\n\n")
        
        # Process each file
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console if RICH_AVAILABLE else None
        ) as progress:
            task = progress.add_task("[cyan]Consolidating migrations...", total=len(migration_files))
            
            for filename in migration_files:
                file_path = os.path.join(MIGRATIONS_DIR, filename)
                
                # Write section header
                outfile.write(f"-- =============================================\n")
                outfile.write(f"-- {filename}\n")
                outfile.write(f"-- =============================================\n")
                
                # Read and write content
                with open(file_path, 'r') as infile:
                    content = infile.read()
                    outfile.write(content)
                    
                    # Ensure there's a newline at the end of each file
                    if not content.endswith('\n'):
                        outfile.write('\n')
                    outfile.write('\n')
                
                progress.update(task, advance=1)
    
    # Backup the old consolidated file if it exists (always do this)
    if os.path.exists(OUTPUT_FILE):
        # Create backup directory if needed
        create_backup_dir()
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_consolidated = os.path.join(BACKUP_DIR, f"consolidated_migration_{timestamp}.sql")
        shutil.copy2(OUTPUT_FILE, backup_consolidated)
        log(f"Existing consolidated file backed up to {backup_consolidated}", "yellow")
    
    # Move the temp file to the final output file
    shutil.move(TEMP_FILE, OUTPUT_FILE)
    
    log(f"Migration files consolidated into {OUTPUT_FILE}", "green")
    log(f"Total files processed: {len(migration_files)}", "green")
    
    # Rename to init file if requested
    if options["rename"]:
        rename_to_init(options["timestamp"])
    
    # Delete original migrations if requested
    if options["delete"]:
        if not options["backup"]:
            log("Warning: Deleting migrations without backup is not allowed", "red")
            return
        
        confirmation = input("Are you sure you want to delete the original migration files? This cannot be undone. (y/N): ")
        if confirmation.lower() == 'y':
            delete_migrations(migration_files)
        else:
            log("Delete operation cancelled", "yellow")

def main():
    """Main function"""
    # Show Sync Supa Migrations header
    if RICH_AVAILABLE:
        console.print(Panel.fit(
            "[bold blue]Sync Supa Migrations[/bold blue]\n[cyan]A tool to consolidate Supabase migrations[/cyan]",
            border_style="green"
        ))
    else:
        print("\n===== Sync Supa Migrations =====")
        print("A tool to consolidate Supabase migrations\n")
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Sync Supa Migrations: Consolidate Supabase migrations")
    parser.add_argument("-b", "--backup", action="store_true", help="Backup original migrations before consolidation")
    parser.add_argument("-d", "--delete", action="store_true", help="Delete original migrations after backup and consolidation")
    parser.add_argument("-r", "--rename", action="store_true", help="Rename consolidated file to init migration")
    parser.add_argument("-t", "--timestamp", type=str, help="Timestamp to use for init migration filename")
    parser.add_argument("-i", "--interactive", action="store_true", help="Use interactive menu for configuration")
    
    args = parser.parse_args()
    
    # Use interactive menu if requested or if no arguments provided
    if args.interactive or (not any([args.backup, args.delete, args.rename, args.timestamp])):
        options = show_menu()
    else:
        options = {
            "backup": args.backup,
            "delete": args.delete,
            "rename": args.rename,
            "timestamp": args.timestamp or datetime.datetime.now().strftime("%Y%m%d")
        }
    
    # Run consolidation with selected options
    consolidate_migrations(options)
    
    if RICH_AVAILABLE:
        console.print("\n[bold green]Operation completed successfully![/bold green]")
    else:
        print("\nOperation completed successfully!")

if __name__ == "__main__":
    main()
