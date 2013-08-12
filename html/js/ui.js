$(document).ready(function() {

    $('#upgrade-needed button').click(function() {
	var installer = new Installer()
	installer.reportStatus = reportInstallationStatus
	startDownload()
	installer.upgrade(endDownload)
    })

    $('#install button').click(function() {
	var packageName = $('#install input').val()
	if (!packageName) 
	    return alert('You have to choose a package name')
	var installer = new Installer()
	installer.reportStatus = reportInstallationStatus
	startDownload()
	installer.install(packageName, endDownload)
    })

    checkState()
})

function checkState() {
    new Installer().checkUpgrade(function(packages) { 
	for (var i=0; i<packages.length; i++)
	    $('<li>').html(packages[i]).appendTo($('#upgrade-needed ul'))
	if (packages.length > 0) {
	    setState('upgrade-needed')
	} else {
	    setState('up-to-date')
	}
    })
}

function reportInstallationStatus(status) {
    if (status.complete && status.numFile == status.totalFiles) {
	$('#download-info').hide()
	$('#download-start').hide()
	$('#download-installing').show()
    } else {
	$('#download-info').show()
	$('#download-start').hide()
	$('#download-installing').hide()
    }
    $('#progressbar').width($('#progressbar-wrapper').width() * status.percent / 100)
    $('#filename').html(status.currentFile)
    $('#file-number').html(status.numFile)
    $('#total-files').html(status.totalFiles)
}

function startDownload() {
    $('#actions').hide()
    $('#progress').show()
    $('#download-info').hide()
    $('#download-start').show()
}

function endDownload() {
    $('#progress').hide()
    $('.state').hide()
    $('#actions').show()
    checkState()
}

function setState(state) {
    $('.state').hide()
    $('#'+state).show()
}

