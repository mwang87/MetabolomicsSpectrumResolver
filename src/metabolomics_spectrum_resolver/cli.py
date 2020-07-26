import click


@click.command()
@click.option('--port', help='The port, defaults to 5000')
@click.option('--host', help='The server, defaults to localhost. Switch to 0.0.0.0 to make externally available')
def main(port, host):
    from metabolomics_spectrum_resolver.app import app
    app.run(port=port, host=host)


if __name__ == '__main__':
    main()
