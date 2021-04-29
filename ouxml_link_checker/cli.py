import click
from .link_checker import link_check_reporter

@click.group()
def cli():
	pass


@cli.command()
@click.argument('path', default='.', type=click.Path(exists=True))
def link_check(path):
	"""Link reports for OU-XML files in specified directory."""
	click.echo('Using file/directory: {}'.format(path))
	link_check_reporter(path)