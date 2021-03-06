import os
import glob
import hashlib
import mimetypes
from flask import Flask, render_template, request, redirect
from flask import url_for, send_from_directory, abort
from werkzeug import secure_filename

# Initialize the Flask application
app = Flask(__name__)

# This is the path to the upload directory
app.config['DATA_FOLDER'] = 'data/'
# This is the path to the processing directory
app.config['PROCESS_FOLDER'] = 'process/'
# These are the extension that we are accepting to be uploaded
file_exts = ['txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif', '.shard']
app.config['ALLOWED_EXTENSIONS'] = set(file_exts)

def setup():
	"""Setup the proper data store directories."""
	if not os.path.exists(app.config['DATA_FOLDER']):
		os.makedirs(app.config['DATA_FOLDER'])
	if not os.path.exists(app.config['PROCESS_FOLDER']):
		os.makedirs(app.config['PROCESS_FOLDER'])


def allowed_file(filename):
	"""For a given file, return whether it's an allowed type or not."""
	return '.' in filename and \
		filename.rsplit('.', 1)[1] in app.config['ALLOWED_EXTENSIONS']

def files_in_cache():
	"""Returns a list of files in the hashserv cache."""
	cache_files = glob.glob(app.config['DATA_FOLDER'] + "/*")
	new_cache_files = []
	for item in cache_files:
		# glob returns the path, so we just want to get the filename
		# because were already know where it is stored
		filelist = item.split("\\")
		new_cache_files.append(filelist[len(filelist)-1])
	return new_cache_files

def get_hash(filepath):
	"""Get the sha256 hash of the passed file."""
	hasher = hashlib.sha256()
	with open(filepath, 'rb') as afile:
		buf = afile.read()
		hasher.update(buf)
	return hasher.hexdigest()


# This route will show a form to perform an AJAX request
# jQuery is loaded to execute the request and update the
# value of the operation.
@app.route('/')
def index(files=None, data_folder=None):
	return render_template('index.html', files=files_in_cache())


# Route that will process the file upload
@app.route('/api/upload', methods=['POST'])
def upload():
	# Get the name of the uploaded file
	file = request.files['file']

	# Check if the file is one of the allowed types/extensions
	if file and allowed_file(file.filename):
		# Make the filename safe, remove unsupported chars
		filename = secure_filename(file.filename)

		try:
			# Move the file from the temporal folder the processing folder
			process_filepath = os.path.join(app.config['PROCESS_FOLDER'],
				filename)
			file.save(process_filepath)

			# Find the hash of the data
			file_hash = get_hash(process_filepath)
			hash_filepath = os.path.join(app.config['DATA_FOLDER'], file_hash)

			# Copy the file from processing to data
			os.rename(process_filepath, hash_filepath)

			# Returns the file hash
			return redirect(url_for('index'))

		except FileExistsError:
			return "Duplicate file."
	else:
		return "Invalid file."


# This route is expecting a parameter containing the name
# of a file. Then it will locate that file on the upload
# directory and show it on the browser, so if the user uploads
# an image, that image is going to be show after the upload
@app.route('/api/download/<filehash>')
def download_file(filehash):
	return send_from_directory(app.config['DATA_FOLDER'], filehash,
		as_attachment=True)

@app.route('/api/serve/<filehash>/<extension>')
def serve_file(filehash, extension):
	# find mimtype from passed extension
	try:
		mimetypes.init()
		mapped_mimetype = mimetypes.types_map["." + extension]
	except KeyError:
		return "415 Unsupported Media Type."

	return send_from_directory(app.config['DATA_FOLDER'], filehash,
		mimetype=mapped_mimetype)


if __name__ == '__main__':
	# Make sure process and data directories are created
	setup()
	
	# Run the Flask app
	app.run(
		host="0.0.0.0",
		port=int("5000"),
		debug=True
	)