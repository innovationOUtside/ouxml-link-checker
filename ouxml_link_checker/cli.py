import click
from .link_checker import link_check_reporter

@click.group()
def cli():
	pass


@cli.command()
@click.argument('path', default='.', type=click.Path(exists=True))
@click.option('--archive', '-a', is_flag=True, help='Archive 200-OK links')
@click.option('--strong-archive', '-A', is_flag=True, help='Archive not 404 links')
def link_check(path, archive, strong_archive):
	"""Link reports for OU-XML files in specified directory."""
	click.echo('Using file/directory: {}'.format(path))
	link_check_reporter(path,archive, strong_archive)