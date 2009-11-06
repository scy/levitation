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
import bz2

# FIXME: With smaller READ_SIZE this tends to crash on the final read?
READ_SIZE = 10240000
ENCODING = 'UTF-8'
IMPORT_MAX = 10
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
		out('blob\nmark :%d\ndata %d\n' % (self.id, len(mydata)))
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

class XMLChunker:
	def __init__(self):
		self.text = self.xml = None
		self.inpage = False
		self.startbyte = self.readbytes = self.imported = 0
		self.meta = Meta(METAFILE) # FIXME: Use a parameter.
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
			Page(self.xml, {'meta': self.meta}).dump()
			self.imported += 1
			if IMPORT_MAX > 0 and self.imported >= IMPORT_MAX:
				sys.exit(0)

progress('Step 1: Creating blobs.')
xc = XMLChunker()
xc.parse()
