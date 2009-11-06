#!/usr/bin/env python


# Hi, and welcome to the code.
# This is currently PoC quality, and I'm no Python God either.
# Patches are encouraged, fork me on GitHub.


import xml.dom.minidom
from xml.parsers.expat import ParserCreate
from calendar import timegm
import codecs
import datetime
import os
import socket
import struct
import sys
import time
import urlparse

# How many bytes to read at once. You probably can leave this alone.
# FIXME: With smaller READ_SIZE this tends to crash on the final read?
READ_SIZE = 10240000
# The encoding for input, output and internal representation. Leave alone.
ENCODING = 'UTF-8'
# Don't import more than this number of _pages_ (not revisions).
IMPORT_MAX = 100
# Where to store meta information. Eats 17 bytes per revision.
METAFILE = '.import-meta'
# Where to store comment information. Eats 257 bytes per revision.
COMMFILE = '.import-comm'
# Where to store author information. Eats 257 bytes per author.
USERFILE = '.import-user'

def singletext(node):
	if len(node.childNodes) == 0:
		return ''
	if len(node.childNodes) != 1:
		raise Exception('singletext has wrong number of children' + node.toxml())
	if node.childNodes[0].nodeType != node.TEXT_NODE:
		raise Exception('singletext child is not text')
	return node.childNodes[0].data

def out(text):
	sys.stdout.write(text)

def progress(text):
	out('progress ' + text + '\n')
	sys.stdout.flush()

class Meta:
	def __init__(self, file):
		self.struct = struct.Struct('LLLLB')
		self.maxrev = -1
		self.fh = open(file, 'wb+')
		self.domain = 'unknown.invalid'
	def write(self, rev, time, page, author, minor):
		flags = 0
		if minor:
			flags += 1
		if author.isip:
			flags += 2
		data = self.struct.pack(
			rev,
			timegm(time.utctimetuple()),
			page,
			author.id,
			flags
			)
		self.fh.seek(rev * self.struct.size)
		self.fh.write(data)
		if self.maxrev < rev:
			self.maxrev = rev
	def read(self, rev):
		self.fh.seek(rev * self.struct.size)
		data = self.fh.read(self.struct.size)
		tuple = self.struct.unpack(data)
		d = {
			'rev':    tuple[0],
			'epoch':  tuple[1],
			'time':   datetime.datetime.utcfromtimestamp(tuple[1]),
			'page':   tuple[2],
			'user':   tuple[3],
			'minor':  False,
			'isip':   False,
			}
		if d['rev'] != 0:
			d['exists'] = True
		else:
			d['exists'] = False
		d['day'] = d['time'].strftime('%Y-%m-%d')
		flags = tuple[4]
		if flags & 1:
			d['minor'] = True
		if flags & 2:
			d['isip'] = True
			d['user'] = socket.inet_ntoa(struct.pack('!I', tuple[3]))
		return d

class StringStore:
	def __init__(self, file):
		self.struct = struct.Struct('Bb255s')
		self.maxid = -1
		self.fh = open(file, 'wb+')
	def write(self, id, text, flags = 1):
		data = self.struct.pack(len(text), flags, text)
		self.fh.seek(id * self.struct.size)
		self.fh.write(data)
		if self.maxid < id:
			self.maxid = id
	def read(self, id):
		self.fh.seek(id * self.struct.size)
		data = self.struct.unpack(self.fh.read(self.struct.size))
		d = {
			'len':   data[0],
			'flags': data[1],
			'text':  data[2][0:data[0]]
			}
		return d

class User:
	def __init__(self, node, meta):
		self.id = -1
		self.name = None
		self.isip = False
		for lv1 in node.childNodes:
			if lv1.nodeType != lv1.ELEMENT_NODE:
				continue
			if lv1.tagName == 'username':
				self.name = singletext(lv1).encode(ENCODING)
			elif lv1.tagName == 'id':
				self.id = int(singletext(lv1))
			elif lv1.tagName == 'ip':
				# FIXME: This is so not-v6-compatible it hurts.
				self.isip = True
				try:
					self.id = struct.unpack('!I', socket.inet_aton(singletext(lv1)))[0]
				except socket.error:
					# IP could not be parsed. Leave ID as -1 then.
					pass
		if not self.isip:
			meta['user'].write(self.id, self.name)

class Revision:
	def __init__(self, node, page, meta):
		self.id = -1
		self.minor = False
		self.timestamp = self.text = self.comment = self.user = None
		self.page = page
		self.meta = meta
		self.dom = node
		for lv1 in self.dom.childNodes:
			if lv1.nodeType != lv1.ELEMENT_NODE:
				continue
			if lv1.tagName == 'id':
				self.id = int(singletext(lv1))
			elif lv1.tagName == 'timestamp':
				self.timestamp = datetime.datetime.strptime(singletext(lv1), "%Y-%m-%dT%H:%M:%SZ")
			elif lv1.tagName == 'contributor':
				self.user = User(lv1, self.meta)
			elif lv1.tagName == 'minor':
				self.minor = True
			elif lv1.tagName == 'comment':
				self.comment = singletext(lv1)
			elif lv1.tagName == 'text':
				self.text = singletext(lv1)
	def dump(self, title):
		self.meta['meta'].write(self.id, self.timestamp, self.page, self.user, self.minor)
		if self.comment:
			self.meta['comm'].write(self.id, self.comment.encode(ENCODING))
		mydata = self.text.encode(ENCODING)
		out('blob\nmark :%d\ndata %d\n' % (self.id + 1, len(mydata)))
		out(mydata + '\n')

class Page:
	def __init__(self, dom, meta):
		self.revisions = []
		self.id = -1
		self.title = ''
		self.meta = meta
		self.dom = dom
		for lv1 in self.dom.documentElement.childNodes:
			if lv1.nodeType != lv1.ELEMENT_NODE:
				continue
			if lv1.tagName == 'title':
				self.title = singletext(lv1)
			elif lv1.tagName == 'id':
				self.id = int(singletext(lv1))
			elif lv1.tagName == 'revision':
				self.revisions.append(Revision(lv1, self.id, self.meta))
	def dump(self):
		progress('   ' + self.title.encode(ENCODING))
		for revision in self.revisions:
			revision.dump(self.title)

class BlobWriter:
	def __init__(self, meta):
		self.text = self.xml = None
		self.intag = self.lastattrs = None
		self.cancel = False
		self.startbyte = self.readbytes = self.imported = 0
		self.meta = meta
		self.fh = codecs.getreader(ENCODING)(sys.stdin)
		self.expat = ParserCreate(ENCODING)
		self.expat.StartElementHandler = self.find_start
	def parse(self):
		while True:
			self.text = self.fh.read(READ_SIZE).encode(ENCODING)
			if not self.text:
				break
			self.startbyte = 0
			self.expat.Parse(self.text)
			if self.cancel:
				return
			if self.intag:
				self.xml += self.text[self.startbyte:]
			self.readbytes += len(self.text)
		self.expat.Parse('', True)
	def find_start(self, name, attrs):
		if name in ('page', 'base', 'namespace'):
			self.intag = name
			self.lastattrs = attrs
			self.expat.StartElementHandler = None
			self.expat.EndElementHandler = self.find_end
			self.startbyte = self.expat.CurrentByteIndex - self.readbytes
			self.xml = ''
	def find_end(self, name):
		if name == self.intag:
			self.intag = None
			self.expat.StartElementHandler = self.find_start
			self.expat.EndElementHandler = None
			endbyte = self.expat.CurrentByteIndex - self.readbytes
			self.xml += self.text[self.startbyte:endbyte] + '</' + name.encode(ENCODING) + '>'
			if self.startbyte == endbyte:
				self.xml = '<' + name.encode(ENCODING) + ' />'
			dom = xml.dom.minidom.parseString(self.xml)
			if name == 'page':
				Page(dom, meta).dump()
				self.imported += 1
				if IMPORT_MAX > 0 and self.imported >= IMPORT_MAX:
					self.expat.StartElementHandler = None
					self.cancel = True
			elif name == 'base':
				self.meta['meta'].domain = urlparse.urlparse(singletext(dom.documentElement)).hostname.encode(ENCODING)
			elif name == 'namespace':
				pass

class Committer:
	def __init__(self, meta):
		self.meta = meta
	def work(self):
		rev = commit = 1
		day = ''
		while rev <= self.meta['meta'].maxrev:
			meta = self.meta['meta'].read(rev)
			comm = self.meta['comm'].read(rev)
			rev += 1
			if not meta['exists']:
				continue
			if meta['minor']:
				minor = ' (minor)'
			else:
				minor = ''
			msg = comm['text'] + '\n\nLevitation import of page %d rev %d%s.\n' % (meta['page'], meta['rev'], minor)
			if commit == 1:
				fromline = ''
			else:
				fromline = 'from :%d\n' % (commit - 1)
			if day != meta['day']:
				day = meta['day']
				progress('   ' + day)
			if meta['isip']:
				author = meta['user']
				authoruid = 'ip-' + author
			else:
				authoruid = 'uid-' + str(meta['user'])
				author = self.meta['user'].read(meta['user'])['text']
			out(
				'commit refs/heads/master\n' +
				'mark :%d\n' % commit +
				'author %s <%s@git.%s> %d +0000\n' % (author, authoruid, self.meta['meta'].domain, meta['epoch']) +
				'committer Importer <importer@FIXME> %d +0000\n' % time.time() +
				'data %d\n%s\n' % (len(msg), msg) +
				fromline +
				'M 100644 :%d %d.mediawiki\n' % (meta['rev'] + 1, meta['page'])
				)
			commit += 1

meta = { # FIXME: Use parameters.
	'meta': Meta(METAFILE),
	'comm': StringStore(COMMFILE),
	'user': StringStore(USERFILE),
	}

progress('Step 1: Creating blobs.')
BlobWriter(meta).parse()

progress('Step 2: Writing commits.')
Committer(meta).work()
