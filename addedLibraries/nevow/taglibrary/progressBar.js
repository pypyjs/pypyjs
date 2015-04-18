function ProgressBar(name) {
	function setPercent(percent) {
		node = document.getElementById(name).firstChild;
		node.style['width'] = percent+'%';
	}
	this.setPercent = setPercent;
}
