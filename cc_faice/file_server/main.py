import os
from argparse import ArgumentParser
from flask import Flask, send_from_directory, request
from werkzeug.utils import secure_filename


DESCRIPTION = 'Run a simple http file server for debugging purposes. USE CAREFULLY: this server does not enable ' \
              'encryption and does not verify credentials for authorization.'


def attach_args(parser):
    parser.add_argument(
        '--bind-host', action='store', type=str, metavar='HOST', default='0.0.0.0',
        help='Bind server to a network interface like "172.17.0.1" (docker) or "127.0.0.1" (localhost). '
             'Default is "0.0.0.0" (all interfaces).'
    )
    parser.add_argument(
        '--bind-port', action='store', type=int, metavar='PORT', default=5000,
        help='Bind server to a tcp port. Default is 5000.'
    )
    parser.add_argument(
        '-u', '--updir', action='store', type=str, metavar='UPDIR', default=os.getcwd(),
        help='Specify a directory for file uploads. Default is current working directory.'
    )
    parser.add_argument(
        '-d', '--downdir', action='store', type=str, metavar='DOWNDIR', default=os.getcwd(),
        help='Specify a directory for file downloads. Default is current working directory.'
    )


def main():
    parser = ArgumentParser(description=DESCRIPTION)
    attach_args(parser)
    args = parser.parse_args()
    return run(**args.__dict__)


def run(bind_host, bind_port, updir, downdir):
    app = Flask('faice file-server')

    @app.route('/<file_name>', methods=['GET'])
    def get_file(file_name):
        """
        .. :quickref: API; Download file
        Download a file specified as <file_name> from DOWNDIR.

        .. sourcecode:: http
            GET /<file_name> HTTP/1.1

        """
        file_name = secure_filename(file_name)
        return send_from_directory(os.path.expanduser(downdir), file_name, as_attachment=True)

    @app.route('/<file_name>', methods=['POST'])
    def post_file(file_name):
        """
        .. :quickref: API; Upload file
        Upload a file specified as <file_name> to UPDIR.

        .. sourcecode:: http
            POST /<file_name> HTTP/1.1

        """
        file_name = secure_filename(file_name)
        file_path = os.path.join(os.path.expanduser(updir), file_name)
        with open(file_path, 'wb') as f:
            f.write(request.data)
        return ''

    app.run(host=bind_host, port=bind_port)
