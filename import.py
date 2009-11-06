#!/usr/bin/env python

import xml.dom.minidom
from xml.parsers.expat import ParserCreate
from calendar import timegm
import codecs
import datetime
import os
from socket import inet_aton, inet_ntoa
import struct
import sys
import time
import bz2

# How many bytes to read at once. You probably can leave this alone.
# FIXME: With smaller READ_SIZE this tends to crash on the final read?
READ_SIZE = 10240000
# The encoding for input, output and internal representation. Leave alone.
ENCODING = 'UTF-8'
# Don't import more than this number of _pages_ (not revisions).
IMPORT_MAX = 100
# Where to store meta information. Eats 17 Bytes per revision.
METAFILE = '.import-meta'

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
			'user':   tuple[3]
			}
		if d['rev'] != 0:
			d['exists'] = True
		else:
			d['exists'] = False
		d['day'] = d['time'].strftime('%Y-%m-%d')
		# FIXME: minor
		return d

class User:
	def __init__(self, node):
		self.id = -1
		self.name = None
		self.isip = False
		for lv1 in node.childNodes:
			if lv1.nodeType != lv1.ELEMENT_NODE:
				continue
			if lv1.tagName == 'username':
				self.name = singletext(lv1)
			elif lv1.tagName == 'id':
				self.id = int(singletext(lv1))
			elif lv1.tagName == 'ip':
				# FIXME: This is so not-v6-compatible it hurts.
				self.id = struct.unpack('!I', inet_aton(singletext(lv1)))[0]
				self.isip = True

class Revision:
	def __init__(self, node, page, meta):
		self.id = -1
		self.minor = False
		self.timestamp = self.text = self.user = None
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
				self.user = User(lv1)
			elif lv1.tagName == 'minor':
				self.minor = True
			elif lv1.tagName == 'text':
				self.text = singletext(lv1)
	def dump(self, title):
		self.meta['meta'].write(self.id, self.timestamp, self.page, self.user, self.minor)
		mydata = self.text.encode(ENCODING)
		out('blob\nmark :%d\ndata %d\n' % (self.id + 1, len(mydata)))
		out(mydata + '\n')

class Page:
	def __init__(self, xmlstring, meta):
		self.revisions = []
		self.id = -1
		self.title = ''
		self.meta = meta
		self.dom = xml.dom.minidom.parseString(xmlstring)
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
		self.inpage = self.cancel = False
		self.startbyte = self.readbytes = self.imported = 0
		self.meta = meta
		self.fh = codecs.getreader(ENCODING)(sys.stdin)
		self.expat = ParserCreate(ENCODING)
		self.expat.StartElementHandler = self.find_page
	def parse(self):
		while True:
			self.text = self.fh.read(READ_SIZE).encode(ENCODING)
			if not self.text:
				break
			self.startbyte = 0
			self.expat.Parse(self.text)
			if self.cancel:
				return
			if self.inpage:
				self.xml += self.text[self.startbyte:]
			self.readbytes += len(self.text)
		self.expat.Parse('', True)
	def find_page(self, name, attrs):
		if name == 'page':
			self.inpage = True
			self.expat.StartElementHandler = None
			self.expat.EndElementHandler = self.find_pageend
			self.startbyte = self.expat.CurrentByteIndex - self.readbytes
			self.xml = ''
	def find_pageend(self, name):
		if name == 'page':
			if not self.inpage:
				raise Exception('not in page!')
			self.inpage = False
			self.expat.StartElementHandler = self.find_page
			self.expat.EndElementHandler = None
			self.xml += self.text[self.startbyte:self.expat.CurrentByteIndex-self.readbytes] + '</' + name.encode(ENCODING) + '>'
			Page(self.xml, meta).dump()
			self.imported += 1
			if IMPORT_MAX > 0 and self.imported >= IMPORT_MAX:
				self.expat.StartElementHandler = None
				self.cancel = True

class Committer:
	def __init__(self, meta):
		self.meta = meta
	def work(self):
		rev = commit = 1
		day = ''
		while rev <= self.meta['meta'].maxrev:
			meta = self.meta['meta'].read(rev)
			rev += 1
			if not meta['exists']:
				continue
			msg = 'Revision %d' % meta['rev']
			if commit == 1:
				fromline = ''
			else:
				fromline = 'from :%d\n' % (commit - 1)
			if day != meta['day']:
				day = meta['day']
				progress('   ' + day)
			out(
				'commit refs/heads/master\n' +
				'mark :%d\n' % commit +
				'author User ID %d <uid-%d@FIXME> %d +0000\n' % (meta['user'], meta['user'], meta['epoch']) +
				'committer Importer <importer@FIXME> %d +0000\n' % time.time() +
				'data %d\n%s\n' % (len(msg), msg) +
				fromline +
				'M 100644 :%d %d.mediawiki\n' % (meta['rev'] + 1, meta['page'])
				)
			commit += 1

meta = {'meta': Meta(METAFILE)} # FIXME: Use a parameter.

progress('Step 1: Creating blobs.')
BlobWriter(meta).parse()

progress('Step 2: Writing commits.')
Committer(meta).work()
