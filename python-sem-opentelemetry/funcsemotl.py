from flask import Flask

app = Flask(__name__)

# Define a sample route that creates a trace
@app.route('/hello')
def hello():
     return 'Hello, World!'

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0')