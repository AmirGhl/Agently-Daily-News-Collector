# Overrides the pyinstaller-hooks-contrib hook for the PyPI package named
# "workflow", which collides with this project's local `workflow` package.
# The contrib hook calls copy_metadata('workflow') and crashes the build
# because our local package has no installed distribution metadata.
datas = []
