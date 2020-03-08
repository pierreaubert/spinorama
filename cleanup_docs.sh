git filter-branch --tree-filter "rm -rf docs" --prune-empty HEAD
git for-each-ref --format="%(refname)" refs/original/ | xargs -n 1 git update-ref -d
git commit -m 'Removing docs from git history'
git gc
git push origin master --force
