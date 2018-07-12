from flask import Flask, jsonify, render_template
import numpy as n

app = Flask(__name__)

@app.route("/")
def index():
    return jsonify((2*n.random.random((15,3))-1).tolist())

@app.route("/bbl/")
def bbl():
    return render_template('bblText.html')

