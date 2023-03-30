def  B_CallFunc(modulecode, funccode, nowruncxt, outcxt, logmode, lognametype, callmethod, g_inputcxt):
    '''
    @组件名称: 参数化功能调用
    @组件风格: 选择型
    @组件类型: 横向参数模块
    @中文注释: 通过输入参数调用内部基础功能模块
    @入参:
        @param    modulecode   str     模块代码
        @param    funccode     str     功能代码
        @param    nowruncxt    dict    当前运行环境输入容器
        @param    outcxt       dict    输出信息容器
        @param    logmode      str     日志模式(1-共享主交易, 2-单独创建)
        @param    lognametype  str     日志名称类型(1-按照模块代码规范 2-按照平台服务代码规范 3-按照外系统报文号规范)
        @param    callmethod   str     调用方式(1-同步接口调用, 3-异步接口调用)
        @param    g_inputcxt     dict    输入信息容器
    @出参:
    @返回状态
        @return    0    调用失败
        @return    1    调用成功
        @return    2    调用异常(已执行完后出现异常)
    @作    者: 张进
    @创建时间: 2011-08-30
    @使用范例:
    '''  
    FLG = 0;    
    Curlogname = None;
    Prevlogname = None;
    oldlogmodulecode = None;
    oldlogfunccode = None;
    try:
        if ((type(nowruncxt) is not dict )or  (type(outcxt) is not dict)):
            return [0, "UPC001", "入参 nowruncxt or outcxt 不合法,非字典",[None]];
        if (type(modulecode) is not str ):
            return [0, "UPC001", "入参模块代码不合法,非字符串", [None]];
        if (type(funccode) is not str ):
            return [0, "UPC001", "入参功能代码不合法,非字符串", [None]];
        if (type(logmode) is not str ):
            return [0, "UPC001", "入参日志模式不合法,非字符串", [None]];
        if (type(lognametype) is not str ):
            return [0, "UPC001", "入参日志名称类型不合法,非字符串", [None]];
        if (type(callmethod) is not str ):
            return [0, "UPC001", "入参调用方式不合法,非字符串", [None]];

        # 防止交易调度自身加特殊判断
        '''
        if nowruncxt["__MC__"] == modulecode and nowruncxt["__TC__"] == funccode:
            return [0,"UPC001", "功能调度时不可自身调用自身" + TC, [None]];
        '''
        
        # 子交易调度不可嵌套,最多只能子交易调度一次,如果有__subcall_dept__则说明是子交易了,不允许后续再进行调度子交易
        #if nowruncxt.has_key("__subcall_dept__"):
        #    return [0,"UPC001", "子交易不可调度其他交易" + TC, [None]];
        
        # 创建输入容器
        input_cxt = {}; 

        input_cxt["modulecode"] = modulecode;
        input_cxt["funccode"]   = funccode;
        input_cxt["templatecode"] = modulecode;
        input_cxt["transcode"]   = funccode;

        # 查询注册的功能,判断功能是否可以被调度
        _ret_ = P_DBExecOneSQL(None, input_cxt, "get_platbasefuncinfo", None, False);
        if _ret_[0] == 0:
            return [0, "UPD999", _ret_[1]+_ret_[2]];
        elif _ret_[0] == 2:
            return [0, "UPD001", "功能[" + modulecode + "_" + funccode + "]未注册,请先配置注册"];

        func_cxt = {};
        for i, item in enumerate(_ret_[3][1]):
            func_cxt[item] = _ret_[3][2][0][i];

        LoggerTrace("func_cxt:" + str(func_cxt));

        if func_cxt["funcstatus"] != "1": # 功能未开放
            return [0, "UPC001", "功能[" + modulecode + "_" + funccode + "]未启用或者已停用"];

        #==== 构造输入输出的公共类信息
        _rsp_ = {};
        trade_pub_var = ["__MC__", "__TC__", "__RCVPCK__", "__VER__"];
        if func_cxt["functype"] == "1": # 是交易
            for item in trade_pub_var:
                input_cxt[item] = "";

            input_cxt["__VER__"] = nowruncxt.get("__VER__","2.31");

            _ModuleName_ = "T"+modulecode+"_"+funccode;
            _EntryName_ = "M"+funccode+"_ENTRY";
        elif func_cxt["functype"] == "2": # 是业务组件
            _ModuleName_ = modulecode;
            _EntryName_ = "COMP_"+funccode+"_ENTRY";
        else:
            return [0, "UPC001", "功能[" + modulecode + "_" + funccode + "]功能类型非法,非现在支持的交易或业务组件"];

        #================================================================================================================
        # 功能: 获取接口信息的内部子函数
        # 输入: 报文号,输入总容器,输出总容器
        # 输出: 无
        # 返回值: 为None则表示成功,否则是错误信息
        #================================================================================================================
        def GetIntefaceInfo(interfacecode, g_inputcxt, outputcxt):
            #==== 获取接口信息
            try:
                _ret_ = P_DBExecOneSQL(None, {"productcode" : "UPBS", "interfacename" : interfacecode}, "get_funcinterface", None, False);
                if _ret_[0] == 0:
                    return _ret_[1]+_ret_[2];
                elif _ret_[0] == 2:
                    return "接口[" + interfacecode + "]未定义";
    
                colname_no    = _ret_[3][1].index("colname");
                colmapname_no = _ret_[3][1].index("colmapname");
                coltype_no    = _ret_[3][1].index("coltype");
                coldefault_no = _ret_[3][1].index("coldefault");
                colmust_no    = _ret_[3][1].index("colmust");
                for line in _ret_[3][2]:
                    value = "";
                    if line[coldefault_no] != None and line[coldefault_no] != "": #默认值处理
                        if not g_inputcxt.has_key(line[colmapname_no]) or g_inputcxt[line[colmapname_no]] in(None, ""):
                            outputcxt[line[colmapname_no]] = line[coldefault_no];
                    else:
                        #==== 取对应的值
                        if g_inputcxt.has_key(line[colmapname_no]):
                            value = g_inputcxt[line[colmapname_no]]
                        else:
                            continue;
    
                        if value == None:
                            continue;
    
                    outputcxt[line[colmapname_no]] = value;

                return None;
            except Exception,e:
                LoggerError(str(format_exc()));
                return str(e);
        #================================================================================================================

        if func_cxt["funcincode"] == "*":
            if g_inputcxt == None or g_inputcxt == {}:
                input_cxt.update(nowruncxt);
            else:
                input_cxt.update(g_inputcxt);

            input_cxt["modulecode"] = modulecode;
            input_cxt["funccode"]   = funccode;
        else:
            if g_inputcxt == None or g_inputcxt == {}:
                _ret_ = GetIntefaceInfo(func_cxt["funcincode"], nowruncxt, input_cxt);
            else:
                _ret_ = GetIntefaceInfo(func_cxt["funcincode"], g_inputcxt, input_cxt);
            if _ret_ != None:
                return [0, "UPD001", "功能[" + modulecode + "_" + funccode + "]处理输入接口[" + func_cxt["funcincode"] + "]异常," + _ret_];

        if lognametype == "2" and nowruncxt.has_key("M_ServiceCode"):
            logmodulecode = nowruncxt.get("M_ServicerNo","UPBS");
            logfunccode   = nowruncxt["M_ServiceCode"];
        elif lognametype == "3" and nowruncxt.has_key("corptradetype"):
            #logmodulecode = nowruncxt.get("syscode","UPBS");
            logmodulecode   = nowruncxt["corptradetype"];
            logfunccode   = "00";
        else:
            logmodulecode = modulecode;
            logfunccode   = funccode;

        if logmode == "2": # 子交易单独创建
            oldlogmodulecode = nowruncxt["__MC__"];
            oldlogfunccode   = nowruncxt["__TC__"];
            ret = AppLoggerChange(logmodulecode, logfunccode, ""); # 日志改名称
            if (ret[0] !=  0):
#                return [0, "UPC999", "日志名称修改为子交易名称时失败," + ret[1] + ret[2]];
                LoggerError("日志名称修改为子交易名称时失败," + ret[1] + ret[2]);
                #return [0, "UPC999", "日志名称修改为子交易名称时失败," + ret[1] + ret[2]];
                input_cxt["__LOG__"] = nowruncxt.get("__LOG__","");
                Prevlogname = nowruncxt.get("__LOG__","");
                Curlogname  = nowruncxt.get("__LOG__","");
            else:
                FLG = 1;
                Prevlogname = ret[3][0];
                Curlogname = ret[3][1];

                nowruncxt["__LOG__"] = Curlogname;
                LoggerTrace("AppLoggerChange BEGIN:" + Curlogname + ":"+Prevlogname);
                
                # 20180705 add by gxj start
                logstmp = ''
                if g_inputcxt == None or g_inputcxt == {}:
                    logstmp = str(nowruncxt.get('__LOGSTMP__', 'None'))
                    seqno = str(nowruncxt.get('__SEQNO__', 'None'))
                    msgid = str(nowruncxt.get('reqmsgid', 'None'))
                    bussno = str(nowruncxt.get('BUSS_SEQ_NO', 'None'))
                    servicecode = str(nowruncxt.get('M_ServiceCode', 'None'))
                else:
                    logstmp = str(g_inputcxt.get('__LOGSTMP__', 'None'))
                    seqno = str(g_inputcxt.get('__SEQNO__', 'None'))
                    msgid = str(g_inputcxt.get('reqmsgid', 'None'))
                    bussno = str(g_inputcxt.get('BUSS_SEQ_NO', 'None'))
                    servicecode = str(g_inputcxt.get('M_ServiceCode', 'None'))
                LoggerInfor("[Log Change Start][SERVICECODE: %s][LOGSTMP: %s][SEQNO: %s][MSGID: %s][BUSS_SEQ_NO: %s]" % (servicecode, logstmp, seqno, msgid, bussno))
                # 20180705 add by gxj end

            if logmode == "2": # 子交易单独创建
                LoggerDebug("当前运行容器信息为:");
                if g_inputcxt == None or g_inputcxt == {}:
                    for item in nowruncxt.keys():
                        LoggerDebug(item + "=" + str(nowruncxt[item]));
                else:
                    for item in g_inputcxt.keys():
                        LoggerDebug(item + "=" + str(g_inputcxt[item]));
            
            # 对于日志名称改变并且当前消息容器中存在mesgdate和mesgid情况,更新消息登记簿,回填消息日志列表
            if nowruncxt.has_key("M_UMesgId"):
                newlogfilename=logmodulecode + "/" + Curlogname;
                P_DBExecOneSQL(None, {"mesgdate" : nowruncxt["M_UMesgId"][:8], "mesgid" : nowruncxt["M_UMesgId"][8:], "newlogfilename" : newlogfilename}, "add_logfilename", None, True);

        if callmethod == "1": # 同步py调用
            _Module_=__import__(_ModuleName_);
            _Method_ = getattr(_Module_, _EntryName_);
            
                
            if func_cxt["functype"] == "1": # 是交易
                input_cxt["templatecode"] = modulecode;
                input_cxt["transcode"]   = funccode;
                input_cxt["__MC__"] = modulecode;
                input_cxt["__TC__"]   = funccode;
                ret = _Method_(input_cxt, _rsp_);
            else:
                ret = _Method_(input_cxt, _rsp_, {}, {});

            LoggerTrace(str(_rsp_));
            FLG = 2;

            if logmode == "2": # 子交易单独创建
                # 20180705 add by gxj start
                if input_cxt is not None:
                    logstmp = str(input_cxt.get('__LOGSTMP__', 'None'))
                    seqno = str(input_cxt.get('__SEQNO__', 'None'))
                    msgid = str(input_cxt.get('reqmsgid', 'None'))
                    bussno = str(input_cxt.get('BUSS_SEQ_NO', 'None'))
                    servicecode = str(input_cxt.get('M_ServiceCode', 'None'))
                    dealcode = str(input_cxt.get('dealcode', 'None'))
                    LoggerInfor("[Log Change End][SERVICECODE: %s][LOGSTMP: %s][SEQNO: %s][MSGID: %s][BUSS_SEQ_NO: %s][DEALCODE: %s]" % (servicecode, logstmp, seqno, msgid, bussno, dealcode))
                # 20180705 add by gxj end
                LoggerInfor("AppLoggerChange END:"+Prevlogname);

                ret2 = AppLoggerChange(oldlogmodulecode, oldlogfunccode, "");
                if (ret2[0] !=  0):
                    LoggerError("日志名称修改回原日志名称时失败," + ret[1] + ret[2]);
                nowruncxt["__LOG__"] = Prevlogname;

                FLG = 3;

            #==== 处理输出信息
            if func_cxt["funcoutcode"] == "*":
                if func_cxt["functype"] == "2": # 是业务组件
                    outcxt.update(_rsp_);
                else:
                    outcxt.update(input_cxt);
            else:
                #==== 获取接口信息
                _ret_ = GetIntefaceInfo(func_cxt["funcoutcode"], _rsp_, outcxt);
                if _ret_ != None:
                    return [2, "UPE999", "功能[" + modulecode + "_" + funccode + "]处理输出接口[" + func_cxt["funcoutcode"] + "]异常," + _ret_];

            if func_cxt["functype"] == "2": # 是业务组件
                if ret == False:  # 说明是失败出口
                    return [0, _rsp_.get("dealcode", ""), _rsp_.get("dealmsg","")];
            else: # 交易
                #outcxt["status"]   =  _rsp_["status"];
                outcxt["dealcode"] =  input_cxt.get("dealcode", "");
                outcxt["dealmsg"]  =  input_cxt.get("dealmsg", "");
                return [1, None, None];

            LoggerTrace(str(ret));
            if(ret == True):
                return [1, None, None];
            else:
                return [2, "UPE999", "子交易调用返回值非True"];
        elif callmethod == "3": # 异步(暂实现为内置的异步)
            '''
            暂通过发送NATP报文到调度模型来解决
            '''
            # ==== 组织请求报文
            input_cxt["callmodulecode"] = modulecode;
            input_cxt["callfunccode"]   = funccode;
            input_cxt["__MC__"] = modulecode;
            input_cxt["__TC__"]   = funccode;
            ret = NATPPack(input_cxt);
            #==== 拆包异常
            if (not type(ret) is list):
                return [2, 'UPC001', 'PyNATP 返回类型不正确', [None]];
            #==== 拆包失败
            elif (len(ret) < 3):
                return [2, 'UPC001', 'PyNATP 返回类型不正确', [None]];
            #==== 拼包异常
            elif ((ret[0]==1) and (not input_cxt.has_key("__SNDPCK__"))):
                return [0, 'UPC001', 'NATP拼包异常:__SNDPCK__ 未生成', [None]];

            LoggerTrace(str(input_cxt));
            LoggerTrace(_rsp_);

            #==== 发起请求
            ret = AFASPDLL.NATPExchange(input_cxt, _rsp_, "127.0.0.1", 9021, 60, 5); 

            LoggerTrace(ret);

            if (not type(ret) is list):
                return [2, 'UPC001', 'NATPExchange返回类型不正确', [None]];
            #====返回结果小于2
            elif (len(ret) < 2 ):
                return [2, 'UPC001', 'NATPExchange返回类型不正确', [None]];
            #====natp交互失败
            if (ret[0]!=0):
                if (ret[1] == 'E'):
                    _rsp_['dealcode'] = 'UPTMOT'
                    _rsp_['dealmsg'] = '通讯超时'
                    retcode = 2;
                else:
                    _rsp_['dealcode'] = 'A0140015'
                    _rsp_['dealmsg'] = '通讯失败'
                    retcode = 0;
                return [retcode, _rsp_['dealcode'], _rsp_['dealmsg'], [None]]

            #==== 解析应答
            NATPUnpack(_rsp_);
            return [1, None, None];
        else:
            return [0, "UPC001", "不支持的调用方式,暂只支持同步py调用", [None]];
    except Exception, e:
        LoggerError(str(format_exc()));
        if logmode == "2": # 子交易单独创建
            if(FLG >=1 and FLG < 3 and Prevlogname != None): # 日志名称更换回原名称
                AppLoggerChange(oldlogmodulecode, oldlogfunccode, "");
                nowruncxt["__LOG__"] = Prevlogname;

        return [2, "UPE999", str(e), None];
