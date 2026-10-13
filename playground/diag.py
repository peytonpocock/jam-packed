# Prints what's wrong in the jam network. Run in the Textport:
#   exec(open(project.folder + '/diag.py').read())
jam = op('/project1/jam')
print('---- diag ----')
for o in sorted(jam.findChildren(depth=1), key=lambda o: o.name):
    e, w = o.errors(), o.warnings()
    if e or w:
        print('{:14s} {} {}'.format(o.name, ('ERROR: ' + e) if e else '', ('warn: ' + w) if w else ''))
for n in ('vid_a', 'vid_b'):
    d = jam.op(n)
    if d:
        print(n, 'file =', d.par.file.eval(), ' size', d.width, 'x', d.height)
eng = jam.op('engine')
if eng:
    print(eng.module.library_summary())
print('out size', jam.op('out').width, 'x', jam.op('out').height, ' input:', [i.name for i in jam.op('out').inputs])
print('---- end ----')
