import click
import json
from .link_checker import link_check_reporter, simple_csv_report

@click.group()
def cli():
	pass


@cli.command()
@click.argument('path', default='.', type=click.Path(exists=True))
@click.option('--archive', '-a', is_flag=True, help='Archive 200-OK links')
@click.option('--strong-archive', '-A', is_flag=True, help='Archive not 404 links')
@click.option('--grab-screenshots', '-s', is_flag=True, help="Grab screenshots.")
def link_check(path, archive, strong_archive, grab_screenshots):
    """Link reports for OU-XML files in specified directory."""
    click.echo('Using file/directory: {}'.format(path))
    link_check_reporter(path, archive, strong_archive, grab_screenshots)


@cli.command()
@click.argument("path", default="broken_links_report.json", type=click.Path(exists=True))
def create_report(path):
	"""Create a report and save it to the specified file path."""
	with open(path, 'r') as f:
		links_report = json.load(f)
	simple_csv_report(links_report, outf="generated_report.csv")
