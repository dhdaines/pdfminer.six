#!/usr/bin/env python2
import sys
from utils import apply_matrix_pt, get_bound, INF
from utils import bsearch, bbox2str, matrix2str, Plane
from pdffont import PDFUnicodeNotDefined


def uniq(objs):
    done = set()
    for obj in objs:
        if obj in done: continue
        done.add(obj)
        yield obj
    return

def csort(objs, key):
    idxs = dict( (obj,i) for (i,obj) in enumerate(objs) )
    return sorted(objs, key=lambda obj:(key(obj), idxs[obj]))


##  LAParams
##
class LAParams(object):

    def __init__(self,
                 writing_mode='lr-tb',
                 line_overlap=0.5,
                 char_margin=2.0,
                 line_margin=0.5,
                 word_margin=0.1,
                 all_texts=False):
        self.writing_mode = writing_mode
        self.line_overlap = line_overlap
        self.char_margin = char_margin
        self.line_margin = line_margin
        self.word_margin = word_margin
        self.all_texts = all_texts
        return

    def __repr__(self):
        return ('<LAParams: char_margin=%.1f, line_margin=%.1f, word_margin=%.1f all_texts=%r>' %
                (self.char_margin, self.line_margin, self.word_margin, self.all_texts))


##  LTItem
##
class LTItem(object):

    def __init__(self, bbox):
        self.set_bbox(bbox)
        return

    def __repr__(self):
        return ('<%s %s>' %
                (self.__class__.__name__, bbox2str(self.bbox)))

    def set_bbox(self, (x0,y0,x1,y1)):
        self.x0 = x0
        self.y0 = y0
        self.x1 = x1
        self.y1 = y1
        self.width = x1-x0
        self.height = y1-y0
        self.bbox = (x0, y0, x1, y1)
        return
        
    def is_hoverlap(self, obj):
        assert isinstance(obj, LTItem)
        return obj.x0 <= self.x1 and self.x0 <= obj.x1

    def hdistance(self, obj):
        assert isinstance(obj, LTItem)
        if self.is_hoverlap(obj):
            return 0
        else:
            return min(abs(self.x0-obj.x1), abs(self.x1-obj.x0))

    def hoverlap(self, obj):
        assert isinstance(obj, LTItem)
        if self.is_hoverlap(obj):
            return min(abs(self.x0-obj.x1), abs(self.x1-obj.x0))
        else:
            return 0

    def is_voverlap(self, obj):
        assert isinstance(obj, LTItem)
        return obj.y0 <= self.y1 and self.y0 <= obj.y1

    def vdistance(self, obj):
        assert isinstance(obj, LTItem)
        if self.is_voverlap(obj):
            return 0
        else:
            return min(abs(self.y0-obj.y1), abs(self.y1-obj.y0))

    def voverlap(self, obj):
        assert isinstance(obj, LTItem)
        if self.is_voverlap(obj):
            return min(abs(self.y0-obj.y1), abs(self.y1-obj.y0))
        else:
            return 0


##  LTPolygon
##
class LTPolygon(LTItem):

    def __init__(self, linewidth, pts):
        self.pts = pts
        self.linewidth = linewidth
        LTItem.__init__(self, get_bound(pts))
        return

    def get_pts(self):
        return ','.join( '%.3f,%.3f' % p for p in self.pts )


##  LTLine
##
class LTLine(LTPolygon):

    def __init__(self, linewidth, p0, p1):
        LTPolygon.__init__(self, linewidth, [p0, p1])
        return


##  LTRect
##
class LTRect(LTPolygon):

    def __init__(self, linewidth, (x0,y0,x1,y1)):
        LTPolygon.__init__(self, linewidth, [(x0,y0), (x1,y0), (x1,y1), (x0,y1)])
        return


##  LTImage
##
class LTImage(LTItem):

    def __init__(self, name, stream, bbox):
        LTItem.__init__(self, bbox)
        self.name = name
        self.stream = stream
        self.srcsize = (stream.get_any(('W', 'Width')),
                        stream.get_any(('H', 'Height')))
        self.imagemask = stream.get_any(('IM', 'ImageMask'))
        self.bits = stream.get_any(('BPC', 'BitsPerComponent'), 1)
        self.colorspace = stream.get_any(('CS', 'ColorSpace'))
        if not isinstance(self.colorspace, list):
            self.colorspace = [self.colorspace]
        return

    def __repr__(self):
        (w,h) = self.srcsize
        return ('<%s(%s) %s %dx%d>' %
                (self.__class__.__name__, self.name,
                 bbox2str(self.bbox), w, h))


##  LTText
##
class LTText(object):

    def __init__(self, text):
        self.text = text
        return

    def __repr__(self):
        return ('<%s %r>' %
                (self.__class__.__name__, self.text))


##  LTAnon
##
class LTAnon(LTText):

    pass


##  LTChar
##
class LTChar(LTItem, LTText):

    debug = 0

    def __init__(self, matrix, font, fontsize, scaling, rise, cid):
        self.matrix = matrix
        self.font = font
        self.fontsize = fontsize
        self.adv = font.char_width(cid) * fontsize * scaling
        try:
            text = font.to_unichr(cid)
            assert isinstance(text, unicode), text
        except PDFUnicodeNotDefined:
            text = '?'
        LTText.__init__(self, text)
        # compute the boundary rectangle.
        if self.font.is_vertical():
            # vertical
            width = font.get_width() * fontsize
            (vx,vy) = font.char_disp(cid)
            if vx is None:
                vx = width/2
            else:
                vx = vx * fontsize * .001
            vy = (1000 - vy) * fontsize * .001
            tx = -vx
            ty = vy + rise
            bll = (tx, ty+self.adv)
            bur = (tx+width, ty)
        else:
            # horizontal
            height = font.get_height() * fontsize
            descent = font.get_descent() * fontsize
            ty = descent + rise
            bll = (0, ty)
            bur = (self.adv, ty+height)
        (a,b,c,d,e,f) = self.matrix
        self.upright = (0 < a*d*scaling and b*c <= 0)
        (x0,y0) = apply_matrix_pt(self.matrix, bll)
        (x1,y1) = apply_matrix_pt(self.matrix, bur)
        if x1 < x0:
            (x0,x1) = (x1,x0)
        if y1 < y0:
            (y0,y1) = (y1,y0)
        LTItem.__init__(self, (x0,y0,x1,y1))
        if self.font.is_vertical():
            self.size = self.width
        else:
            self.size = self.height
        return

    def __repr__(self):
        if self.debug:
            return ('<%s %s matrix=%s font=%r fontsize=%.1f adv=%s text=%r>' %
                    (self.__class__.__name__, bbox2str(self.bbox), 
                     matrix2str(self.matrix), self.font, self.fontsize,
                     self.adv, self.text))
        else:
            return '<char %r>' % self.text

    def is_compatible(self, obj):
        """Returns True if two characters can coexist in the same line."""
        return True

    
##  LTContainer
##
class LTContainer(LTItem):

    def __init__(self, bbox):
        LTItem.__init__(self, bbox)
        self._objs = []
        return

    def __iter__(self):
        return iter(self._objs)

    def __len__(self):
        return len(self._objs)

    def add(self, obj):
        self._objs.append(obj)
        return

    def extend(self, objs):
        for obj in objs:
            self.add(obj)
        return


##  LTExpandableContainer
##
class LTExpandableContainer(LTContainer):

    def __init__(self):
        LTContainer.__init__(self, (+INF,+INF,-INF,-INF))
        return

    def add(self, obj):
        LTContainer.add(self, obj)
        self.set_bbox((min(self.x0, obj.x0), min(self.y0, obj.y0),
                       max(self.x1, obj.x1), max(self.y1, obj.y1)))
        return

    def finish(self):
        return self


##  LTTextLine
##
class LTTextLine(LTExpandableContainer, LTText):

    def __init__(self, word_margin):
        LTExpandableContainer.__init__(self)
        self.word_margin = word_margin
        return

    def __repr__(self):
        return ('<%s %s %r>' %
                (self.__class__.__name__, bbox2str(self.bbox), self.text))

    def finish(self):
        LTContainer.add(self, LTAnon('\n'))
        self.text = ''.join( obj.text for obj in self if isinstance(obj, LTText) )
        return LTExpandableContainer.finish(self)

    def find_neighbors(self, plane, ratio):
        raise NotImplementedError

class LTTextLineHorizontal(LTTextLine):

    def __init__(self, word_margin):
        LTTextLine.__init__(self, word_margin)
        self._x1 = +INF
        return

    def add(self, obj):
        if isinstance(obj, LTChar) and self.word_margin:
            margin = self.word_margin * obj.width
            if self._x1 < obj.x0-margin:
                LTContainer.add(self, LTAnon(' '))
        self._x1 = obj.x1
        LTTextLine.add(self, obj)
        return

    def find_neighbors(self, plane, ratio):
        h = ratio*self.height
        objs = plane.find((self.x0, self.y0-h, self.x1, self.y1+h))
        return [ obj for obj in objs if isinstance(obj, LTTextLineHorizontal) ]
    
class LTTextLineVertical(LTTextLine):

    def __init__(self, word_margin):
        LTTextLine.__init__(self, word_margin)
        self._y0 = -INF
        return

    def add(self, obj):
        if isinstance(obj, LTChar) and self.word_margin:
            margin = self.word_margin * obj.height
            if obj.y1+margin < self._y0:
                LTContainer.add(self, LTAnon(' '))
        self._y0 = obj.y0
        LTTextLine.add(self, obj)
        return
        
    def find_neighbors(self, plane, ratio):
        w = ratio*self.width
        objs = plane.find((self.x0-w, self.y0, self.x1+w, self.y1))
        return [ obj for obj in objs if isinstance(obj, LTTextLineVertical) ]
    

##  LTTextBox
##
##  A set of text objects that are grouped within
##  a certain rectangular area.
##
class LTTextBox(LTExpandableContainer):

    def __init__(self):
        LTExpandableContainer.__init__(self)
        self.index = None
        return

    def __repr__(self):
        return ('<%s(%s) %s %r...>' %
                (self.__class__.__name__, self.index,
                 bbox2str(self.bbox), self.text[:20]))

    def finish(self):
        self.text = ''.join( obj.text for obj in self if isinstance(obj, LTTextLine) )
        return LTExpandableContainer.finish(self)

class LTTextBoxHorizontal(LTTextBox):
    
    def finish(self):
        self._objs = csort(self._objs, key=lambda obj: -obj.y1)
        return LTTextBox.finish(self)

class LTTextBoxVertical(LTTextBox):

    def finish(self):
        self._objs = csort(self._objs, key=lambda obj: -obj.x1)
        return LTTextBox.finish(self)


##  LTTextGroup
##
class LTTextGroup(LTExpandableContainer):

    def __init__(self, objs):
        LTExpandableContainer.__init__(self)
        self.extend(objs)
        return

class LTTextGroupLRTB(LTTextGroup):
    
    def finish(self):
        # reorder the objects from top-left to bottom-right.
        self._objs = csort(self._objs, key=lambda obj: obj.x0+obj.x1-(obj.y0+obj.y1))
        return LTTextGroup.finish(self)

class LTTextGroupTBRL(LTTextGroup):
    
    def finish(self):
        # reorder the objects from top-right to bottom-left.
        self._objs = csort(self._objs, key=lambda obj: -(obj.x0+obj.x1)-(obj.y0+obj.y1))
        return LTTextGroup.finish(self)


##  LTLayoutContainer
##
class LTLayoutContainer(LTContainer):

    def __init__(self, bbox, laparams=None):
        LTContainer.__init__(self, bbox)
        self.laparams = laparams
        self.layout = None
        return
        
    def finish(self):
        """Perform the layout analysis."""
        if self.laparams is None: return
        # textobjs is a list of LTChar objects, i.e.
        # it has all the individual characters in the page.
        (textobjs, otherobjs) = self.get_textobjs(self._objs)
        if not textobjs: return
        textlines = list(self.get_textlines(textobjs,
                                            self.laparams.line_overlap,
                                            self.laparams.char_margin,
                                            self.laparams.word_margin))
        assert len(textobjs) <= sum( len(line._objs) for line in textlines )
        textboxes = list(self.get_textboxes(textlines, self.laparams.line_margin))
        assert len(textlines) == sum( len(box._objs) for box in textboxes )
        top = self.group_textboxes(textboxes)
        def assign_index(obj, i):
            if isinstance(obj, LTTextBox):
                obj.index = i
                i += 1
            elif isinstance(obj, LTTextGroup):
                for x in obj:
                    i = assign_index(x, i)
            return i
        assign_index(top, 0)
        textboxes.sort(key=lambda box:box.index)
        self._objs = textboxes + otherobjs
        self.layout = top
        return self

    def get_textobjs(self, objs):
        """Split all the objects in the page into text-related objects and others."""
        textobjs = []
        otherobjs = []
        for obj in objs:
            if isinstance(obj, LTChar):
                textobjs.append(obj)
            else:
                otherobjs.append(obj)
        return (textobjs, otherobjs)

    def get_textlines(self, objs, line_overlap, char_margin, word_margin):
        obj0 = None
        line = None
        for obj1 in objs:
            if obj0 is not None:
                k = 0
                if (obj0.is_compatible(obj1) and obj0.is_voverlap(obj1) and 
                    min(obj0.height, obj1.height) * line_overlap < obj0.voverlap(obj1) and
                    obj0.hdistance(obj1) < max(obj0.width, obj1.width) * char_margin):
                    # obj0 and obj1 is horizontally aligned:
                    #
                    #   +------+ - - -
                    #   | obj0 | - - +------+   -
                    #   |      |     | obj1 |   | (line_overlap)
                    #   +------+ - - |      |   -
                    #          - - - +------+
                    #
                    #          |<--->|
                    #        (char_margin)
                    k |= 1
                if (obj0.is_compatible(obj1) and obj0.is_hoverlap(obj1) and 
                    min(obj0.width, obj1.width) * line_overlap < obj0.hoverlap(obj1) and
                    obj0.vdistance(obj1) < max(obj0.height, obj1.height) * char_margin):
                    # obj0 and obj1 is vertically aligned:
                    #
                    #   +------+
                    #   | obj0 |
                    #   |      |
                    #   +------+ - - -
                    #     |    |     | (char_margin)
                    #     +------+ - -
                    #     | obj1 |
                    #     |      |
                    #     +------+
                    #
                    #     |<-->|
                    #   (line_overlap)
                    k |= 2
                if ( (k & 1 and isinstance(line, LTTextLineHorizontal)) or
                     (k & 2 and isinstance(line, LTTextLineVertical)) ):
                    line.add(obj1)
                elif line is not None:
                    yield line.finish()
                    line = None
                else:
                    if k == 2:
                        line = LTTextLineVertical(word_margin)
                        line.add(obj0)
                        line.add(obj1)
                    elif k == 1:
                        line = LTTextLineHorizontal(word_margin)
                        line.add(obj0)
                        line.add(obj1)
                    else:
                        line = LTTextLineHorizontal(word_margin)
                        line.add(obj0)
                        yield line.finish()
                        line = None
            obj0 = obj1
        if line is None:
            line = LTTextLineHorizontal(word_margin)
            line.add(obj0)
        yield line.finish()
        return

    def get_textboxes(self, lines, line_margin):
        plane = Plane(lines)
        for line in lines:
            plane.add(line)
        plane.finish()
        boxes = {}
        for line in lines:
            neighbors = line.find_neighbors(plane, line_margin)
            assert line in neighbors, line
            members = []
            for obj1 in neighbors:
                members.append(obj1)
                if obj1 in boxes:
                    members.extend(boxes.pop(obj1))
            if isinstance(line, LTTextLineHorizontal):
                box = LTTextBoxHorizontal()
            else:
                box = LTTextBoxVertical()
            for obj in uniq(members):
                box.add(obj)
                boxes[obj] = box
        done = set()
        for line in lines:
            box = boxes[line]
            if box in done: continue
            done.add(box)
            yield box.finish()
        return

    def group_textboxes(self, boxes):
        def dist(obj1, obj2):
            """A distance function between two TextBoxes.
            
            Consider the bounding rectangle for obj1 and obj2.
            Return its area less the areas of obj1 and obj2, 
            shown as 'www' below. This value may be negative.
            +------+..........+
            | obj1 |wwwwwwwwww:
            +------+www+------+
            :wwwwwwwwww| obj2 |
            +..........+------+
            """
            return ((max(obj1.x1,obj2.x1) - min(obj1.x0,obj2.x0)) * 
                    (max(obj1.y1,obj2.y1) - min(obj1.y0,obj2.y0)) -
                    (obj1.width*obj1.height + obj2.width*obj2.height))
        boxes = boxes[:]
        # XXX this is slow when there're many textboxes.
        while 2 <= len(boxes):
            mindist = INF
            minpair = None
            boxes = csort(boxes, key=lambda obj: obj.width*obj.height)
            for i in xrange(len(boxes)):
                for j in xrange(i+1, len(boxes)):
                    (obj1, obj2) = (boxes[i], boxes[j])
                    d = dist(obj1, obj2)
                    if d < mindist:
                        mindist = d
                        minpair = (obj1, obj2)
            assert minpair
            (obj1, obj2) = minpair
            boxes.remove(obj1)
            boxes.remove(obj2)
            if (isinstance(obj1, LTTextBoxVertical) or
                isinstance(obj1, LTTextGroupTBRL)):
                group = LTTextGroupTBRL([obj1, obj2])
            else:
                group = LTTextGroupLRTB([obj1, obj2])
            boxes.append(group.finish())
        assert len(boxes) == 1
        return boxes.pop()
    

##  LTFigure
##
class LTFigure(LTLayoutContainer):

    def __init__(self, name, bbox, matrix, laparams=None):
        self.name = name
        self.matrix = matrix
        (x,y,w,h) = bbox
        bbox = get_bound( apply_matrix_pt(matrix, (p,q))
                          for (p,q) in ((x,y), (x+w,y), (x,y+h), (x+w,y+h)) )
        LTLayoutContainer.__init__(self, bbox, laparams=laparams)
        return

    def __repr__(self):
        return ('<%s(%s) %s matrix=%s>' %
                (self.__class__.__name__, self.name,
                 bbox2str(self.bbox), matrix2str(self.matrix)))

    def finish(self):
        if self.laparams is None or not self.laparams.all_texts: return
        return LTLayoutContainer.finish(self)


##  LTPage
##
class LTPage(LTLayoutContainer):

    def __init__(self, pageid, bbox, rotate=0, laparams=None):
        LTLayoutContainer.__init__(self, bbox, laparams=laparams)
        self.pageid = pageid
        self.rotate = rotate
        return

    def __repr__(self):
        return ('<%s(%r) %s rotate=%r>' %
                (self.__class__.__name__, self.pageid,
                 bbox2str(self.bbox), self.rotate))
