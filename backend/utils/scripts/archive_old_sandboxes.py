#!/usr/bin/env python
"""
Script to archive sandboxes for projects that are older than 1 day.

Usage:
    python archive_old_sandboxes.py [--days N] [--dry-run]

This script:
1. Gets all projects from the projects table
2. Filters projects created more than N days ago (default: 1 day)
3. Archives the sandboxes for those projects

Make sure your environment variables are properly set:
- SUPABASE_URL
- SUPABASE_SERVICE_ROLE_KEY
- DAYTONA_SERVER_URL
"""

import asyncio
import sys
import os
import argparse
from typing import List, Dict, Any
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Load script-specific environment variables
load_dotenv(".env")

from services.supabase import DBConnection
from sandbox.sandbox import daytona
from utils.logger import logger

# Global DB connection to reuse
db_connection = None


async def get_old_projects(days_threshold: int = 1) -> List[Dict[str, Any]]:
    """
    Query all projects created more than N days ago.
    
    Args:
        days_threshold: Number of days threshold (default: 1)
        
    Returns:
        List of projects with their sandbox information
    """
    global db_connection
    if db_connection is None:
        db_connection = DBConnection()
    
    client = await db_connection.client
    
    # Print the Supabase URL being used
    print(f"Using Supabase URL: {os.getenv('SUPABASE_URL')}")
    
    # Calculate the date threshold
    threshold_date = (datetime.now() - timedelta(days=days_threshold)).isoformat()
    
    # Initialize variables for pagination
    all_projects = []
    page_size = 1000
    current_page = 0
    has_more = True
    
    logger.info(f"Starting to fetch projects older than {days_threshold} day(s)")
    print(f"Looking for projects created before: {threshold_date}")
    
    # Paginate through all projects
    while has_more:
        # Query projects with pagination
        start_range = current_page * page_size
        end_range = start_range + page_size - 1
        
        logger.info(f"Fetching projects page {current_page+1} (range: {start_range}-{end_range})")
        
        try:
            result = await client.table('projects').select(
                'project_id',
                'name',
                'created_at',
                'account_id',
                'sandbox'
            ).range(start_range, end_range).execute()
            
            # Debug info - print raw response
            print(f"Response data length: {len(result.data)}")
            
            if not result.data:
                print("No more data returned from query, ending pagination")
                has_more = False
            else:
                # Print a sample project to see the actual data structure
                if current_page == 0 and result.data:
                    print(f"Sample project data: {result.data[0]}")
                
                all_projects.extend(result.data)
                current_page += 1
                
                # Progress update
                logger.info(f"Loaded {len(all_projects)} projects so far")
                print(f"Loaded {len(all_projects)} projects so far...")
                
                # Check if we've reached the end - if we got fewer results than the page size
                if len(result.data) < page_size:
                    print(f"Got {len(result.data)} records which is less than page size {page_size}, ending pagination")
                    has_more = False
                else:
                    print(f"Full page returned ({len(result.data)} records), continuing to next page")
                    
        except Exception as e:
            logger.error(f"Error during pagination: {str(e)}")
            print(f"Error during pagination: {str(e)}")
            has_more = False  # Stop on error
    
    # Print the query result summary
    total_projects = len(all_projects)
    print(f"Found {total_projects} total projects in database")
    logger.info(f"Total projects found in database: {total_projects}")
    
    if not all_projects:
        logger.info("No projects found in database")
        return []
    
    # Filter projects that are older than the threshold and have sandbox information
    old_projects_with_sandboxes = [
        project for project in all_projects
        if project.get('created_at') and project.get('created_at') < threshold_date
        and project.get('sandbox') and project['sandbox'].get('id')
    ]
    
    logger.info(f"Found {len(old_projects_with_sandboxes)} old projects with sandboxes")
    
    # Print a few sample old projects for debugging
    if old_projects_with_sandboxes:
        print("\nSample of old projects with sandboxes:")
        for i, project in enumerate(old_projects_with_sandboxes[:3]):
            print(f"  {i+1}. {project.get('name')} (Created: {project.get('created_at')})")
            print(f"     Sandbox ID: {project['sandbox'].get('id')}")
            if i >= 2:
                break
    
    return old_projects_with_sandboxes


async def archive_sandbox(project: Dict[str, Any], dry_run: bool) -> bool:
    """
    Archive a single sandbox.
    
    Args:
        project: Project information containing sandbox to archive
        dry_run: If True, only simulate archiving
        
    Returns:
        True if successful, False otherwise
    """
    sandbox_id = project['sandbox'].get('id')
    project_name = project.get('name', 'Unknown')
    project_id = project.get('project_id', 'Unknown')
    created_at = project.get('created_at', 'Unknown')
    
    try:
        logger.info(f"Checking sandbox {sandbox_id} for project '{project_name}' (ID: {project_id}, Created: {created_at})")
        
        if dry_run:
            logger.info(f"DRY RUN: Would archive sandbox {sandbox_id}")
            print(f"Would archive sandbox {sandbox_id} for project '{project_name}' (Created: {created_at})")
            return True
        
        # Get the sandbox
        sandbox = daytona.get_current_sandbox(sandbox_id)
        
        # Check sandbox state - it must be stopped before archiving
        sandbox_info = sandbox.info()
        
        # Log the current state
        logger.info(f"Sandbox {sandbox_id} is in '{sandbox_info.state}' state")
        
        # Only archive if the sandbox is in the stopped state
        if sandbox_info.state == "stopped":
            logger.info(f"Archiving sandbox {sandbox_id} as it is in stopped state")
            sandbox.archive()
            logger.info(f"Successfully archived sandbox {sandbox_id}")
            return True
        else:
            logger.info(f"Skipping sandbox {sandbox_id} as it is not in stopped state (current: {sandbox_info.state})")
            return True
            
    except Exception as e:
        import traceback
        error_type = type(e).__name__
        stack_trace = traceback.format_exc()
        
        # Log detailed error information
        logger.error(f"Error processing sandbox {sandbox_id}: {str(e)}")
        logger.error(f"Error type: {error_type}")
        logger.error(f"Stack trace:\n{stack_trace}")
        
        # If the exception has a response attribute (like in HTTP errors), log it
        if hasattr(e, 'response'):
            try:
                response_data = e.response.json() if hasattr(e.response, 'json') else str(e.response)
                logger.error(f"Response data: {response_data}")
            except Exception:
                logger.error(f"Could not parse response data from error")
        
        print(f"Failed to process sandbox {sandbox_id}: {error_type} - {str(e)}")
        return False


async def process_sandboxes(old_projects: List[Dict[str, Any]], dry_run: bool) -> tuple[int, int]:
    """
    Process all sandboxes sequentially.
    
    Args:
        old_projects: List of projects older than the threshold
        dry_run: Whether to actually archive sandboxes or just simulate
        
    Returns:
        Tuple of (processed_count, failed_count)
    """
    processed_count = 0
    failed_count = 0
    
    if dry_run:
        logger.info(f"DRY RUN: Would archive {len(old_projects)} sandboxes")
    else:
        logger.info(f"Archiving {len(old_projects)} sandboxes")
    
    print(f"Processing {len(old_projects)} sandboxes...")
    
    # Process each sandbox sequentially
    for i, project in enumerate(old_projects):
        success = await archive_sandbox(project, dry_run)
        
        if success:
            processed_count += 1
        else:
            failed_count += 1
        
        # Print progress periodically
        if (i + 1) % 20 == 0 or (i + 1) == len(old_projects):
            progress = (i + 1) / len(old_projects) * 100
            print(f"Progress: {i + 1}/{len(old_projects)} sandboxes processed ({progress:.1f}%)")
            print(f"  - Processed: {processed_count}, Failed: {failed_count}")
    
    return processed_count, failed_count


async def main():
    """Main function to run the script."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Archive sandboxes for projects older than N days')
    parser.add_argument('--days', type=int, default=1, help='Age threshold in days (default: 1)')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be archived without actually archiving')
    args = parser.parse_args()

    logger.info(f"Starting sandbox cleanup for projects older than {args.days} day(s)")
    if args.dry_run:
        logger.info("DRY RUN MODE - No sandboxes will be archived")
    
    # Print environment info
    print(f"Environment Mode: {os.getenv('ENV_MODE', 'Not set')}")
    print(f"Daytona Server: {os.getenv('DAYTONA_SERVER_URL', 'Not set')}")
    
    try:
        # Initialize global DB connection
        global db_connection
        db_connection = DBConnection()
        
        # Get all projects older than the threshold
        old_projects = await get_old_projects(args.days)
        
        if not old_projects:
            logger.info(f"No projects older than {args.days} day(s) with sandboxes to process")
            print(f"No projects older than {args.days} day(s) with sandboxes to archive.")
            return
        
        # Print summary of what will be processed
        print("\n===== SANDBOX CLEANUP SUMMARY =====")
        print(f"Projects older than {args.days} day(s): {len(old_projects)}")
        print(f"Sandboxes that will be archived: {len(old_projects)}")
        print("===================================")
        
        logger.info(f"Found {len(old_projects)} projects older than {args.days} day(s)")
        
        # Ask for confirmation before proceeding
        if not args.dry_run:
            print("\n⚠️  WARNING: You are about to archive sandboxes for old projects ⚠️")
            print("This action cannot be undone!")
            confirmation = input("\nAre you sure you want to proceed with archiving? (TRUE/FALSE): ").strip().upper()
            
            if confirmation != "TRUE":
                print("Archiving cancelled. Exiting script.")
                logger.info("Archiving cancelled by user")
                return
            
            print("\nProceeding with sandbox archiving...\n")
            logger.info("User confirmed sandbox archiving")
        
        # List a sample of projects to be processed
        for i, project in enumerate(old_projects[:5]):  # Just show first 5 for brevity
            created_at = project.get('created_at', 'Unknown')
            project_name = project.get('name', 'Unknown')
            project_id = project.get('project_id', 'Unknown')
            sandbox_id = project['sandbox'].get('id')
            
            print(f"{i+1}. Project: {project_name}")
            print(f"   Project ID: {project_id}")
            print(f"   Created At: {created_at}")
            print(f"   Sandbox ID: {sandbox_id}")
            
        if len(old_projects) > 5:
            print(f"   ... and {len(old_projects) - 5} more projects")
        
        # Process all sandboxes
        processed_count, failed_count = await process_sandboxes(old_projects, args.dry_run)
        
        # Print final summary
        print("\nSandbox Cleanup Summary:")
        print(f"Total projects older than {args.days} day(s): {len(old_projects)}")
        print(f"Total sandboxes processed: {len(old_projects)}")
        
        if args.dry_run:
            print(f"DRY RUN: No sandboxes were actually archived")
        else:
            print(f"Successfully processed: {processed_count}")
            print(f"Failed to process: {failed_count}")
        
        logger.info("Sandbox cleanup completed")
            
    except Exception as e:
        logger.error(f"Error during sandbox cleanup: {str(e)}")
        sys.exit(1)
    finally:
        # Clean up database connection
        if db_connection:
            await DBConnection.disconnect()


if __name__ == "__main__":
    asyncio.run(main()) 