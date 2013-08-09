/*
 * Copyright 2012-2013 AGR Audio, Industria e Comercio LTDA. <contato@portalmod.com>
 * 
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 * 
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 * 
 * You should have received a copy of the GNU General Public License
 * along with this program.  If not, see <http://www.gnu.org/licenses/>.
 *
 * This handles software upgrade. Steps are:
 *   - Synchronize package database
 *   - 
 */

function Installer() {
    var self = this

    this.update = function(callback) {
	var trans = new Transference(REPOSITORY,
				     '/system/update',
				     'mod.db.tar.gz');
	trans.reportFinished = callback
	trans.start()
    }

    this.upgrade = function() {
	this.update(function() {
	    $.ajax({
		method: 'get',
		url: '/system/upgrade/dependencies',
		success: function(packages) {
		    self.download(packages, self.doUpgrade)
		}
	    })
	})
    }

    this.doUpgrade = function() {
	$.ajax({
	    method: 'get',
	    url: '/system/upgrade',
	    success: self.finish
	})
    }

    this.install = function(packageName) {
	this.update(function() {
	    $.ajax({
		method: 'get',
		url: '/system/package/dependencies/'+packageName,
		success: function(packages) {
		    self.download(packages, 
				  function() {
				      self.doInstall(packageName)
				  })
		}
	    })
	})
    }

    this.doInstall = function(packageName) {
	$.ajax({
	    method: 'get',
	    url: '/system/package/install/'+packageName,
	    success: self.finish
	})
    }

    this.download = function(packages, callback) {
	var processNext = function() {
	    if (packages.length == 0)
		return callback()
	    var fileName = packages.shift()
	    var trans = new Transference(REPOSITORY,
					 '/system/package/download',
					 fileName)
	    trans.reportFinished = processNext
	    trans.start()
	}
	processNext()
    }
}
