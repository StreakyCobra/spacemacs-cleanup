#!/usr/bin/env python
# -*- coding: utf-8 -*-
# pylint: disable=invalid-name
"""Script to help cleaning Github issues."""

import argparse
import datetime
import json
import random
import shelve
import sys
from collections import defaultdict
from pprint import pprint

import requests

PRGNAME = sys.argv[0]
"""str: Name of the program."""

REPO = 'spacemacs'
"""str: Name of the repository."""

USER = 'syl20bnr'
"""str: Name of the repository owner."""

API_URL = 'https://api.github.com/repos/{}/{}/issues'.format(USER, REPO)
"""str: The URL for the issues API."""

BASE_URL = 'https://github.com'
"""str: Name of the repository owner."""

REPORT_URL = '{}/{}/{}/issues/3549'.format(BASE_URL, USER, REPO)
"""str: URL for reporting used in user's message."""

INFO_URL = '{}/{}/{}/wiki/Autumnal-Cleanup-2015'.format(
    BASE_URL, USER, REPO)
"""str: URL for information used in user's message."""

FLAGS_URL = '{}#flags'.format(INFO_URL)
"""str: URL for flags information used in user's message."""

MAX_PAGINATION = 10
"""int: The max pagination to reach. Used to avoid infinite loop.

Beware, Github's requests limitation is 60 per hour for unauthenticated access.
"""

DB_PATH = 'cleanup.db'
"""str: The path to the file database."""

ARGS = None
"""Command line arguments."""


def get_issues():
    """Get all open issues from the Github repository."""
    # Placeholder for issues (paged yet)
    paged_issues = []
    # Go over the pagination
    for page in range(1, MAX_PAGINATION):
        # Get issues
        url = API_URL + '?page={}&per_page=100'.format(page)
        request = requests.get(url)
        if not request.ok:
            print("An error occurs.", file=sys.stderr)
            sys.exit(1)
        issues = json.loads(request.content.decode('utf8'))
        # Append them to the paginated list
        paged_issues.append(issues)
        # Stop the loop if no more issues
        if not issues:
            break
    # Flatten the issues from pagination
    return [issue for issues in paged_issues for issue in issues]


def store_issues(issues, db):
    """Store the issues in the database (owerwrite the database)."""
    db.clear()
    for issue in issues:
        num = str(issue['number'])
        db[num] = dict()
        db[num]['issue'] = issue
        db[num]['assignee'] = None
        db[num]['assign_date'] = None
        db[num]['report_date'] = None


def cmd_build_db(db):
    """Build the database by populating it with all commits.

    Arguments:
        db (dict): The database to build.
    """
    issues = get_issues()
    store_issues(issues, db)


def cmd_print_db(db):
    """Print the database.

    Arguments:
        db (dict): The database to print.
    """
    pprint(dict(db))


def cmd_trigger_db(db):
    """Trigger a refresh of the database to free oldly assigned issues."""
    for key in sorted(db.keys(), key=int):
        item = db[key]
        day_age = None if item['assign_date'] is None \
            else (datetime.date.today() - item['assign_date']).days
        if item['report_date'] is None and \
           item['assign_date'] is not None and \
           day_age is not None and \
           day_age > 14:
            item['assignee'] = None
            item['assign_date'] = None
            print("Freeing #{} ({})".format(key, item['assignee']))


def cmd_list(db, user, labels=None):
    """Print a list of issues in a human readable format.

    Also generate a ready-to-paste message for the given user.

    Arguments:
        db (dict): The database.
        user (Optional[str]): Name of the user, used to prepare the message.
        labels (Optional[str]): Take only issues having one of the labels.
    """
    keys = list(db.keys())
    if user is not None:
        keys = [key for key in keys if db[key]['assignee'] == user]
    if labels is not None:
        keys = [key for key in keys
                if set(labels).intersection(
                    label['name'] for label in db[key]['issue']['labels'])]
    for key in sorted(keys, key=int):
        assignee = db[key]['assignee']
        assign_date = db[key]['assign_date']
        report_date = db[key]['report_date']
        title = db[key]['issue']['title']
        print('[{}] '.format('X' if report_date else ' '), end='')
        print('#{:4s} ('.format(key), end='')
        print('{:8},'.format(assignee[:8] if assignee else ''), end='')
        if assign_date is not None:
            print(' {:%Y-%m-%d},'.format(assign_date if assign_date else ''),
                  end='')
        else:
            print(' ' * 11 + ',', end='')
        if report_date is not None:
            print(' {:%Y-%m-%d}'.format(report_date if report_date else ''),
                  end='')
        else:
            print(' ' * 11, end='')
        print('): {:8s}'.format(title))


def cmd_random(db, user, number, labels=None):
    """Extract the given number of random issues from the database.

    Also generate a ready-to-paste message for the given user.

    Arguments:
        db (dict): The database.
        user (str): Name of the user, used to prepare the message.
        number (int): Number of random issues to take.
        labels (Optional[str]): Take only issues having one of the labels.
    """
    # Subset of not-assigned issues
    subset = [str(key) for key in db.keys() if db[key]['assignee'] is None]
    # Filter by labels if any
    if labels is not None:
        subset = [key for key in subset
                  if set(labels).intersection(
                      label['name'] for label in db[key]['issue']['labels'])]
    # Generate list of issues
    chosen = []
    for _ in range(number):
        # Check if there is still candidates
        if not subset:
            break
        # Choose a candidate
        num = random.choice(subset)
        subset.remove(num)
        # Save it
        chosen.append(num)
    # Generate the next command, to simplify my life
    print('{} assign -u {} -i {}'.format(
        PRGNAME, user, ' '.join(sorted(chosen, key=int))))
    # Print the message to send
    print('\n------- MESSAGE IS FOLLOWING -------\n')
    print('@{} Here are some issues for you:'.format(user))
    print()
    for num in sorted(chosen, key=int):
        issue = db[num]['issue']
        print('- #{} **{}**'.format(num, issue['title']), end='')
        labels = ' | '.join([l['name'] for l in issue['labels']])
        if labels:
            print(' *{}*'.format(labels))
        else:
            print()
    print()
    print('Please confirm you take them, so I can block those ones for the '
          'next 2 weeks :-)\n')


def cmd_assign(db, user, issues):
    """Assign the given issues to the user.

    Also generate a ready-to-paste message for the given user.

    Arguments:
        db (dict): The database.
        user (str): Name of the user, used to prepare the message.
        issues (List[str]): Issues to assign to the user.
    """
    # Save as assigned
    for issue in issues:
        db[issue]['assignee'] = user
        db[issue]['assign_date'] = datetime.date.today()
    # Print the message to send.
    print('\n------- MESSAGE IS FOLLOWING -------\n')
    print('@{} Here is the canvas you can use for reporting:'.format(user))
    print('```')
    for val in issues:
        print('- [ ] #{} Not verified'.format(val))
    print('```')
    print('Once checked, please report them [here]({}) by changing the '
          'commit\'s flag from `Not verified` to '
          '[the appropriate one]({}).'.format(REPORT_URL, FLAGS_URL))
    print()


def cmd_report(db, user, issues):
    """Report the given issues as treated.

    Arguments:
        db (dict): The database.
        user (str): Name of the user, used to prepare the message.
        issues (List[str]): Issues to assign to the user.
    """
    # Save as reported
    for issue in issues:
        db[issue]['assignee'] = user
        db[issue]['report_date'] = datetime.date.today()
    # Compute statistics
    count = len(issues)
    total = len([1 for key in db
                 if db[key]['assignee'] == user
                 if db[key]['report_date'] is not None])
    rest = [key for key in db.keys()
            if db[key]['assignee'] == user
            if db[key]['report_date'] is None]
    # Print the message to send.
    print('\n------- MESSAGE IS FOLLOWING -------\n')
    print('@{} Thank you very much for helping with issues cleanup :-) :+1:'
          '\nYou verified {} issues this time, and {} in total.'.format(
              user, count, total))
    print('These issues are still waiting for reporting from your part:')
    for key in rest:
        print('- #{}'.format(key))
    print()


def cmd_stats(db):
    """Report the database stats.

    Arguments:
        db (dict): The database.
    """
    counts = defaultdict(int)
    for key in db.keys():
        if db[key]['report_date'] is not None:
            counts[db[key]['assignee']] += 1
    counts_total = sum([counts[key] for key in counts])
    total = len(db)
    reported = len([key for key in db.keys()
                    if db[key]['report_date'] is not None])
    # Print
    print()
    print('Some statistics about the :fallen_leaf: [Autumnal Cleanup 2015]({})'
          ' progress:\n'.format(INFO_URL))
    print("Contributions:")
    for user in sorted(counts, key=lambda x: counts[x], reverse=True):
        print('- {}: {} ({:.2%})'.format(
            user, counts[user], counts[user]/counts_total))
    print()
    print('Overall progress: {}/{} ({:.2%})'.format(
        reported, total, reported/total))
    print()
    print('Go read the the description page if you want to be part of it :-)')
    print()


def parse_arguments():
    """Parse command line arguments."""
    # Prepare the parser
    parser = argparse.ArgumentParser(
        description='Script to help cleaning Github issues.')
    # Add flags
    parser.add_argument('action',
                        choices=(
                            'build_db',
                            'print_db',
                            'trigger_db',
                            'list',
                            'random',
                            'assign',
                            'report',
                            'stats',
                        ),
                        help='the command to execute.')
    parser.add_argument('--issues', '-i',
                        type=str, nargs="+", default=[],
                        help='filter on issues.')
    parser.add_argument('--labels', '-l',
                        type=str, nargs="+",
                        help='filter on labels.')
    parser.add_argument('--number', '-n',
                        type=int, default=5,
                        help='filter on labels.')
    parser.add_argument('--user', '-u',
                        type=str,
                        help='name of the user.')
    # Parse and return arguments
    return parser.parse_args()


def main():
    """Run the script."""
    with shelve.open(DB_PATH, writeback=True) as db:

        if ARGS.action == 'build_db':
            cmd_build_db(db)

        if ARGS.action == 'print_db':
            cmd_print_db(db)

        if ARGS.action == 'trigger_db':
            cmd_trigger_db(db)

        if ARGS.action == 'list':
            cmd_list(db, ARGS.user, ARGS.labels)

        if ARGS.action == 'random':
            # Check arguments
            if ARGS.user is None:
                print("Please provide an user with '-u'.", file=sys.stderr)
                sys.exit(1)
            if not ARGS.number:
                print("Please provide a number with '-n'.", file=sys.stderr)
                sys.exit(1)
            cmd_random(db, ARGS.user, ARGS.number, ARGS.labels)

        if ARGS.action == 'assign':
            # Check arguments
            if ARGS.user is None:
                print("Please provide an user with '-u'.", file=sys.stderr)
                sys.exit(1)
            cmd_assign(db, ARGS.user, ARGS.issues)

        if ARGS.action == 'report':
            # Check arguments
            if ARGS.user is None:
                print("Please provide an user with '-u'.", file=sys.stderr)
                sys.exit(1)
            cmd_report(db, ARGS.user, ARGS.issues)

        if ARGS.action == 'stats':
            cmd_stats(db)


if __name__ == '__main__':
    ARGS = parse_arguments()
    main()
