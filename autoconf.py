import pygit2
import unidiff

repo = pygit2.Repository('.')

head = repo.head.get_object()
head_parent = repo.revparse_single('HEAD~2')
diff = repo.diff(head_parent, head)
patch = unidiff.PatchSet(diff.patch)
