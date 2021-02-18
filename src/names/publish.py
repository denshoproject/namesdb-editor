def make_hosts(text):
    hosts = []
    for host in text.split(','):
        h,p = host.split(':')
        hosts.append( {'host':h, 'port':p} )
    return hosts
