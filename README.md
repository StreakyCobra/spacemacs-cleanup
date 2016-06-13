spacemacs-cleanup
=================

This is the script that has been used for the Autumnal Cleanup 2015 of
Spacemacs.

Typical workflow
----------------

1. Prepare the database of issues:

        ./cleanup.py build_db

2. Get random issues for an user. This output A) a markdown message that can be
   pasted to gitter asking the user to confirm; and B) the command to assign the
   issues:

        ./cleanup.py random -u StreakyCobra -n 10 -l "OS X" "Python"

3. Assign the given issues to the user (can by copy/pasted from the output of
   the previous command). Display a message that can be pasted to Gitter showing
   him the template for reporting:

        ./cleanup.py assign -u StreakyCobra -i 3930 4208 4955 5806 5957

4. Once the user has reported the issues on the bug tracker, mark them has
   reported. This display an information message to the user showing him
   remaining assigned issues:

        ./cleanup.py report -u StreakyCobra -i 3930 4208 4955 5806 5957

5. Repeat steps 2 to 4 as many times as needed.

6. It is possible anytime to check issues status with:

        ./cleanup.py list

7. Once in a while, it's possible to get statistics about the progress of the
   ongoing cleanup that can directly printed to gitter with:

        ./cleanup.py stats

Usage
-----

```bash
# Get all open issues and PR from Github
./cleanup.py build_db

# Print the content of the database (raw output)
./cleanup.py print_db

# List all issues in the database (pretty output)
./cleanup.py list

# Get 10 random issues for StreakyCobra labelled as "OS X" or "Python"
./cleanup.py random -u StreakyCobra -n 10 -l "OS X" "Python"

# The output of the previous command print the assign command to validate
assignation to an user
./cleanup.py assign -u StreakyCobra -i 3930 4208 4955 5806 5957

# Save inside the database that the given user has reported the specified issues
./cleanup.py report -u StreakyCobra -i 3930 4208 4955 5806 5957

# Print statistics about the ongoing cleanup
./cleanup.py stats
```
