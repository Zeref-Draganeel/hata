﻿# -*- coding: utf-8 -*-
__all__ = ('PermOW', 'Role', 'cr_p_overwrite_object', 'cr_p_role_object', )

from .bases import DiscordEntity
from .client_core import ROLES
from .others import random_id
from .color import Color
from .permission import Permission
from .user import PartialUser
from .preconverters import preconvert_snowflake, preconvert_str, preconvert_color, preconvert_int, preconvert_bool, \
    preconvert_flag

from . import ratelimit

def PartialRole(role_id):
    try:
        return ROLES[role_id]
    except KeyError:
        pass
    
    role=object.__new__(Role)
    role.id=role_id
    
    role.color=Color(0)
    role.guild=None
    role.separated=False
    # id is set up
    role.managed=False
    role.mentionable=False
    role.name=''
    role.permissions=Permission.permission_none
    role.position=1 # 0 is default role, so we go for 1
    
    ROLES[role_id]=role
    
    return role

class Role(DiscordEntity, immortal=True):
    __slots__ = ('color', 'guild', 'separated', 'managed', 'mentionable', 'name', 'permissions', 'position',)
    
    def __new__(cls,data,guild):
        role_id=int(data['id'])
        try:
            role=ROLES[role_id]
            update=(role.guild is None)
        except KeyError:
            role=object.__new__(cls)
            role.id=role_id
            update=True
            ROLES[role_id]=role
            
        if update:
            
            guild.all_role[role.id]=role
            role.guild=guild
            
            role.name=data['name']
            
            role.position=data.get('position',0)
            
            role.color=Color(data.get('color',0))

            role.permissions=Permission(data['permissions'])
            
            role.separated=data.get('hoist',False)
            role.managed=data.get('managed',False)
            role.mentionable=data.get('mentionable',False)

            guild.roles.append_halfchecked(role)
        
        return role

    @classmethod
    def precreate(cls, role_id, **kwargs):
        role_id = preconvert_snowflake(role_id, 'role_id')
        
        if kwargs:
            processable = []
            
            try:
                name = kwargs.pop('name')
            except KeyError:
                pass
            else:
                name = preconvert_str(name, 'name', 2, 32)
                processable.append(('name',name))
            
            for key in ('managed', 'mentionable', 'separated',):
                try:
                    value = kwargs.pop(key)
                except KeyError:
                    pass
                else:
                    value = preconvert_bool(value, key)
                    processable.append((key,value))
            
            try:
                position = kwargs.pop('position')
            except KeyError:
                pass
            else:
                position = preconvert_int(position, 'position', 0, 250)
                processable.append(('position', position))
            
            try:
                permissions = kwargs.pop('permissions')
            except KeyError:
                pass
            else:
                permissions = preconvert_flag(permissions, 'permissions', Permission)
                processable.append(('permissions',permissions))
            
            try:
                color = kwargs.pop('color')
            except KeyError:
                pass
            else:
                color = preconvert_color(color)
                processable.append(('color',color))
            
            if kwargs:
                raise TypeError(f'Unused or unsettable attributes: {kwargs}')
        
        else:
            processable = None
        
        try:
            role=ROLES[role_id]
        except KeyError:
            role=object.__new__(cls)
            role.id=role_id
            
            role.color      = Color()
            role.guild      = None
            role.separated  = False
            role.managed    = False
            role.mentionable= False
            role.name       = ''
            role.permissions= Permission.permission_none
            role.position   = 1
            ROLES[role_id]  = role
        else:
            if (role.guild is not None):
                return role
        
        if (processable is not None):
            for item in processable:
                setattr(role, *item)
        
        return role

    def _update_no_return(self,data):
        position=data['position']
        if self.position!=position:
            self.guild.roles.switch(self,position)
            
        self.name=data['name']
        self.permissions=Permission(data['permissions'])
        self.color=Color(data['color'])
        self.separated=data['hoist']
        self.managed=data['managed']
        self.mentionable=data['mentionable']
        self.guild._cache_perm.clear()
        
    def __str__(self):
        return self.name

    def __repr__(self):
        return f'<{self.__class__.__name__} name={getattr(self,"name","partial")} ({self.id})>'

    def _update(self,data):
        old={}
        
        name=data['name']
        if self.name!=name:
            old['name']=self.name
            self.name=name
                
        permissions=Permission(data['permissions'])
        if self.permissions!=permissions:
            old['permissions']=self.permissions
            self.permissions=permissions

        color=data['color']
        if self.color!=color:
            old['color']=self.color
            self.color=Color(color)

        separated=data['hoist']
        if self.separated!=separated:
            old['separated']=self.separated
            self.separated=separated

        managed=data['managed']
        if self.managed!=managed:
            old['managed']=self.managed
            self.managed=managed

        mentionable=data['mentionable']
        if self.mentionable!=mentionable:
            old['mentionable']=self.mentionable
            self.mentionable=mentionable
        
        position=data['position']
        if self.position!=position:
            old['position']=self.position
            self.guild.roles.switch(self,position)
        
        self.guild._cache_perm.clear()
        return old

    def _delete(self):
        guild=self.guild
        if guild is None:
            return #already deleted

        self.guild=None
        
        del guild.roles[self.position]
        del guild.all_role[self.id]
        
        guild._cache_perm.clear()
        
        for user in guild.users.values():
            try:
                profile=user.guild_profiles[guild]
            except KeyError:
                #the user has no GuildProfile, it supposed to be impossible
                continue
            try:
                profile.roles.remove(self)
            except ValueError:
                pass

    @property
    def is_default(self):
       return self.position==0

    @property
    def mention(self):
        return f'<@&{self.id}>'
    
    def __format__(self,code):
        if not code:
            return getattr(self,'name','Partial')
        if code=='m':
            return f'<@&{self.id}>'
        if code=='c':
            return f'{self.created_at:%Y.%m.%d-%H:%M:%S}'
        raise ValueError(f'Unknown format code {code!r} for object of type {self.__class__.__name__!r}')
    
    @property
    def users(self):
        guild=self.guild
        if guild.id==self.id:
            return list(guild.users.values())
        role_id=self.id
        return [user for user in guild.users if self in user.guild_profiles[guild].roles]

    @property
    def partial(self):
        return (self.guild is None)

    def __gt__(self,other):
        if type(self) is type(other):
            if self.position > other.position:
                return True
            
            if self.position == other.position:
                if self.id>other.id:
                    return True
        
            return False
        
        return NotImplemented
    
    def __ge__(self,other):
        if type(self) is type(other):
            if self.position > other.position:
                return True
            
            if self.position == other.position:
                if self.id >= other.id:
                    return True
            
            return False
        
        return NotImplemented
    
    def __le__(self,other):
        if type(self) is type(other):
            if self.position < other.position:
                return True
            
            if self.position == other.position:
                if self.id <= other.id:
                    return True
            
            return False
        
        return NotImplemented
    
    def __lt__(self,other):
        if type(self) is type(other):
            if self.position < other.position:
                return True
            
            if self.position == other.position:
                if self.id < other.id:
                    return True
            
            return False
        
        return NotImplemented

#permission overwrite
class PermOW(object):
    __slots__=('allow', 'deny', 'target',)

    def __init__(self,data):
        id_=int(data['id'])
        if data['type']=='role':
            self.target=PartialRole(id_)
        else:
            self.target=PartialUser(id_)
        self.allow=data['allow']
        self.deny=data['deny']
        
    def __hash__(self):
        return self.target.id^self.allow^self.deny
    
    def __repr__(self):
        return f'<{self.__class__.__name__} target={self.target!r}>'

    def keys(self):
        return Permission.__keys__.keys()

    __iter__=keys

    def values(self):
        allow=self.allow
        deny=self.deny
        for index in Permission.__keys__.values():
            if (allow>>index)&1:
                yield 'a'
            if (deny>>index)&1:
                yield 'd'
            yield 'n'

    def items(self):
        allow=self.allow
        deny=self.deny
        for key,index in Permission.__keys__.items():
            if (allow>>index)&1:
                yield key,'a'
            if (deny>>index)&1:
                yield key,'d'
            yield key,'n'

    def __getitem__(self,key):
        index=Permission.__keys__[key]
        if (self.allow>>index)&1:
            return 'a'
        if (self.deny>>index)&1:
            return 'd'
        return 'n'

    @property
    def type(self):
        if type(self.target) is Role:
            return 'role'
        return 'member'
    
    def __lt__(self,other):
        if type(self) is not type(other):
            return NotImplemented
        
        if type(self.target) is Role:
            if type(other.target) is Role:
                if self.target.id<other.target.id:
                    return True
                return False
            return True
        if type(other.target) is Role:
            return True
        if self.target.id<other.target.id:
            return True
        return False
        
    def __eq__(self,other):
        if type(self) is not type(other):
            return NotImplemented
        
        if self.target.id!=other.target.id:
            return False
        
        if self.allow!=other.allow:
            return False
        
        if self.deny!=other.deny:
            return False
        
        return True
    
    def __gt__(self,other):
        if type(self) is not type(other):
            return NotImplemented
        
        if type(self.target) is Role:
            if type(other.target) is Role:
                if self.target.id>other.target.id:
                    return True
                return False
            return False
        if type(other.target) is Role:
            return False
        if self.target.id>other.target.id:
            return True
        return True
    
def cr_p_role_object(name, id_=None, color=Color(0), separated=False,
        position=0, permissions=Permission(0), managed=False,
        mentionable=False):
    
    if id_ is None:
        id_=random_id()
    
    return {
        'id'            : id_,
        'name'          : name,
        'color'         : color,
        'hoist'         : separated,
        'position'      : position,
        'permissions'   : permissions,
        'managed'       : managed,
        'mentionable'   : mentionable,
            }

def cr_p_overwrite_object(target,allow,deny):
    return {
        'allow' : allow,
        'deny'  : deny,
        'id'    : target.id,
        'type'  : 'role' if type(target) is Role else 'member',
            }


ratelimit.Role = Role

del ratelimit
del DiscordEntity