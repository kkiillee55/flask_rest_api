from flask import Flask,jsonify,request,render_template
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from datetime import datetime
from math import ceil

application=Flask(__name__)
application.config['SQLALCHEMY_DATABASE_URI']= 'mysql+pymysql://root:12345678@localhost/flask'
db=SQLAlchemy(application)
bcrypt=Bcrypt(application)

class User(db.Model):
    id=db.Column(db.Integer,primary_key=True)
    last_name=db.Column(db.String(50),unique=False,nullable=False)
    first_name=db.Column(db.String(50),unique=False,nullable=False)
    email=db.Column(db.String(120),unique=True,nullable=False)
    password=db.Column(db.String(60),nullable=False)
    status=db.Column(db.String(20),nullable=True)
    date_created=db.Column(db.DateTime,nullable=False,default=datetime.utcnow)

    def __repr__(self):
        return f'id:{self.id}, name:{self.last_name}.{self.first_name}, email:{self.email}\n'

class Address(db.Model):
    id=db.Column(db.Integer,primary_key=True)
    street1=db.Column(db.String(200),unique=False,nullable=False)
    street2=db.Column(db.String(200),unique=False,nullable=False)
    city=db.Column(db.String(30),nullable=False)
    state = db.Column(db.String(30), nullable=False)
    country=db.Column(db.String(30),nullable=False)
    postal_code=db.Column(db.String(30),nullable=False)

    def __repr__(self):
        return f'address: {self.street1} -- {self.street2} -- {self.postal_code}\n'

def jsonify_users(users):
    res=[]
    for user in users:
        res.append({'id':user.id,'first_name':user.first_name,'last_name':user.last_name,'email':user.email,'password':user.password,'status':user.status})
    return res

def jsonfy_addrs(addrs):
    res=[]
    for addr in addrs:
        res.append({'street1': addr.street1,'street2':addr.street2,'city':addr.city,'state':addr.state,'country':addr.country,'postal_code':addr.postal_code})
    return res

def pagination(dbClass,jsonify_func,url,start,limit):
    data_rows=dbClass.query.all()
    count=len(data_rows)
    if count<start:
        return jsonify({'message':'we dont have that many rows','code':404})
    res={}
    res['start']=start
    res['limit']=limit
    res['count']=count
    if start==1:
        res['previous']=''
    else:
        res['previous']=url+'?start={}&limit={}'.format(max(1,start-limit),max(5,min(limit,count-start)))

    if start+limit>count:
        res['next']=''
    else:
        res['next']=url+'?start={}&limit={}'.format(start+limit,limit)
    res['results']=jsonify_func(data_rows[start-1:start-1+limit])
    return jsonify(res)

#user_columns=[['first_name',str],['last_name',str],['email',str],['password',str],['status',str]]
user_columns=[{'attrname':'first_name','datatype':str},
              {'attrname':'last_name','datatype':str},
              {'attrname':'email','datatype':str,'unique':True},
              {'attrname':'password','datatype':str},
              {'attrname':'status','datatype':str,'nullable':True},]

#address_columns=[['street1',str],['street2',str],['city',str],['state',str],['country',str],['postal_code',str]]
address_columns=[{'attrname':'street1','datatype':str},
                 {'attrname':'street2','datatype':str},
                 {'attrname':'city','datatype':str},
                 {'attrname':'state','datatype':str},
                 {'attrname':'country','datatype':str},
                 {'attrname':'postal_code','datatype':str}]

def validate_args(db_columns,db_class,args):
    data=db_class()
    res={'code':None,'message':{}}
    commitData=True
    for row in db_columns:
        if row['attrname'] not in args:
            res['code']=500
            res['message'][row['attrname']]=f"{row['attrname']} is not found"
            commitData=False
        else:
            if row['datatype']!=type(args[row['attrname']]):
                res['message'][row['attrname']] = f"{row['attrname']} Datatype is wrong, {row['datatype']} is expected, {type(type(args[row['attrname']]))} is given"
                commitData = False
            else:
                if 'nullable' not in row and not args[row['attrname']]:
                    res['message'][row['attrname']] = f"{row['attrname']} cannot be empty"
                    commitData = False
                elif 'unique' in row and db_class.query.filter_by(**{row['attrname']:args[row['attrname']]}).first():
                    res['message'][row['attrname']] = f"{row['attrname']} is already taken, please choose another one"
                    commitData = False
                else:
                    if row['attrname']!='password':
                        setattr(data,row['attrname'],args[row['attrname']])
                    else:
                        setattr(data, row['attrname'], bcrypt.generate_password_hash(args[row['attrname']]).decode('utf-8'))
    if commitData:
        db.session.add(data)
        db.session.commit()
        res['message']['success']=True
        res['code']=200
    else:
        res['message']['success'] = False
        res['code'] = 500
    return jsonify(res)



@application.route('/')
def home():
    return jsonify({'message':'this is home page\n to get user info, goto /User \n to get address info goto /Address','code':200})

@application.route('/User/page', methods=['GET'])
def get_user():
    start=request.args.get('start',1,type=int)
    limit=request.args.get('limit',5,type=int)
    #print(start,limit)
    return pagination(User,jsonify_users,'/User/page',start,limit)


def pagination_id(dbClass,jsonify_func,url,pageid=1,limit=5):
    #limit is maximum number of entries to show,default is 5
    #pageid start from 1
    total_pages = ceil(dbClass.query.count() / limit)
    if pageid<1:
        pageid=1
    elif pageid>total_pages:
        pageid=total_pages
    data=dbClass.query.limit(limit).offset((pageid-1)*limit).all()

    res={}
    res['page']=pageid
    res['total_pages']=total_pages
    res['results']=jsonify_func(data)
    res['previous']=url+'/'+str(max(1,pageid-1))
    res['next']=url+'/'+str(min(total_pages,pageid+1))
    return jsonify(res)

@application.route('/User/page/<int:pageid>',methods=['GET'])
def get_user_page(pageid):
    return pagination_id(User,jsonify_users,'/User/page',pageid)


@application.route('/User/add', methods=['POST'])
def add_user():
    args=request.json
    print(args)
    msg=validate_args(user_columns,User,args)
    return msg

def update_data_attr(data,db_columns,args):
    for column_name,column_datatype in db_columns:
        if column_name in args and column_datatype==type(args[column_name]):
            if column_name!='password':
                setattr(data, column_name, args[column_name])
            else:
                setattr(data, column_name, bcrypt.generate_password_hash(args[column_name]).decode('utf-8'))
    db.session.commit()
    return jsonify({'message':'data Updated','code':200})

@application.route('/User/<int:user_id>', methods=['GET', 'PATCH', 'DELETE'])
def update_user(user_id):
    user=User.query.get(user_id)
    args=request.json
    #print(args)
    if not user:
        return jsonify({'message':'user not found','code':404})

    if request.method=='GET':
        return jsonify(jsonify_users([user,]))

    elif request.method=='PATCH':
        update_data_attr(user,user_columns, args)
        return jsonify({'message': 'user updated', 'code': 200})

    else:
        db.session.delete(user)
        db.session.commit()
        return jsonify({'message': 'user deleted', 'code': 200})

@application.route('/Address/page', methods=['GET'])
def get_addr():
    start=request.args.get('start',1,type=int)
    limit=request.args.get('limit',5,type=int)
    return pagination(Address,jsonfy_addrs,'/Address/page',start,limit)

@application.route('/Address/add', methods=['POST'])
def add_addr():
    args=request.json
    msg=validate_args(address_columns,Address,args)
    return msg


@application.route('/Address/<int:addr_id>', methods=['GET', 'PATCH', 'DELETE'])
def update_addr(addr_id):
    addr=Address.query.get(addr_id)
    args=request.json
    if not addr:
        return jsonify({'message':'address not found','code':404})
    if request.method=='GET':
        return jsonify(jsonfy_addrs([addr,]))
    elif request.method=='PATCH':
        update_data_attr(addr,address_columns,args)
        return jsonify({'message': 'address updated', 'code': 200})
    else:
        db.session.delete(addr)
        db.session.commit()
        return jsonify({'message': 'address deleted', 'code': 200})



@application.route('/test')
def test():
    return render_template('simpleAJAX/test.html')





if __name__=='__main__':
    application.run(debug=True)

