"""
三维共振选股系统 - 核心模块
============================
基于"大势定仓位，板块定方向，个股定买卖"的递进逻辑

核心指标：
- RPS（相对强度指标）：衡量标的相对基准的超额收益
- DBQR（对比强弱指标）：直观对比个股与大盘的强弱
- DBQRV（对比强弱量）：量能配合验证
- BIAS（乖离率）：结合大盘判断抗跌性/领涨性

使用方法:
    from three_dimension_selection import ThreeDimensionSelector
    
    selector = ThreeDimensionSelector()
    results = selector.run_full_workflow()
"""
import os
import json
import time
import requests
from datetime import datetime, timedelta


class ThreeDimensionSelector:
    """三维共振选股器"""
    
    def __init__(self, db_path=None):
        """
        初始化选股器
        
        Args:
            db_path: 数据库路径，默认使用项目data/market_data.db
        """
        if db_path is None:
            import os
            db_path = os.path.join(os.path.dirname(__file__), 'data', 'market_data.db')
        
        self.db_path = db_path
        self.data_source = MorningDataSource()
        
        # 加载历史数据
        self.history_data = self._load_history_data()
    
    def _load_history_data(self) -> dict:
        """
        从数据库加载历史K线数据
        
        Returns:
            dict: {code: [{'date', 'open', 'close', 'high', 'low', 'volume', 'amount'}, ...]}
        """
        import sqlite3
        
        history = {}
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 获取所有有历史数据的股票
            cursor.execute('''
                SELECT code, date, open, close, high, low, volume, amount
                FROM stock_klines
                ORDER BY code, date
            ''')
            
            rows = cursor.fetchall()
            
            # 按股票代码分组
            current_code = None
            current_klines = []
            
            for row in rows:
                code = row[0]
                if code != current_code:
                    # 保存上一个股票的数据
                    if current_code and current_klines:
                        history[current_code] = current_klines
                    
                    # 开始新股票
                    current_code = code
                    current_klines = []
                
                current_klines.append({
                    'date': row[1],
                    'open': row[2],
                    'close': row[3],
                    'high': row[4],
                    'low': row[5],
                    'volume': row[6],
                    'amount': row[7]
                })
            
            # 保存最后一个股票
            if current_code and current_klines:
                history[current_code] = current_klines
            
            conn.close()
            print(f"[ThreeDimension] 从数据库加载 {len(history)} 只股票历史数据")
            
        except Exception as e:
            print(f"[ThreeDimension] 加载历史数据失败: {e}")
        
        return history
        
        Args:
            db_path: 数据库路径，默认使用项目data/market_data.db
        """
        if db_path is None:
            import os
            db_path = os.path.join(os.path.dirname(__file__), 'data', 'market_data.db')
        
        self.db_path = db_path
        self.data_source = MorningDataSource()
        
        # 加载历史数据
        self.history_data = self._load_history_data()
    
    def _load_history_data(self) -> dict:
        """
        从数据库加载历史K线数据
        
        Returns:
            dict: {code: [{'date', 'open', 'close', 'high', 'low', 'volume', 'amount'}, ...]}
        """
        import sqlite3
        
        history = {}
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 获取所有有历史数据的股票
            cursor.execute('''
                SELECT code, date, open, close, high, low, volume, amount
                FROM stock_klines
                ORDER BY code, date
            ''')
            
            rows = cursor.fetchall()
            
            # 按股票代码分组
            current_code = None
            current_klines = []
            
            for row in rows:
                code = row[0]
                if code != current_code:
                    # 保存上一个股票的数据
                    if current_code and current_klines:
                        history[current_code] = current_klines
                    
                    # 开始新股票
                    current_code = code
                    current_klines = []
                
                current_klines.append({
                    'date': row[1],
                    'open': row[2],
                    'close': row[3],
                    'high': row[4],
                    'low': row[5],
                    'volume': row[6],
                    'amount': row[7]
                })
            
            # 保存最后一个股票
            if current_code and current_klines:
                history[current_code] = current_klines
            
            conn.close()
            print(f"[ThreeDimension] 从数据库加载 {len(history)} 只股票历史数据")
            
        except Exception as e:
            print(f"[ThreeDimension] 加载历史数据失败: {e}")
        
        return history
        
        Args:
            db_path: 数据库路径，默认使用项目data/market_data.db
        """
        if db_path is None:
            import os
            db_path = os.path.join(os.path.dirname(__file__), 'data', 'market_data.db')
        
        self.db_path = db_path
        self.data_source = MorningDataSource()
        
        # 加载历史数据
        self.history_data = self._load_history_data()
    
    def _load_history_data(self) -> dict:
        """
        从数据库加载历史K线数据
        
        Returns:
            dict: {code: [{'date', 'open', 'close', 'high', 'low', 'volume', 'amount'}, ...]}
        """
        import sqlite3
        
        history = {}
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 获取所有有历史数据的股票
            cursor.execute('''
                SELECT code, date, open, close, high, low, volume, amount
                FROM stock_klines
                ORDER BY code, date
            ''')
            
            rows = cursor.fetchall()
            
            # 按股票代码分组
            current_code = None
            current_klines = []
            
            for row in rows:
                code = row[0]
                if code != current_code:
                    # 保存上一个股票的数据
                    if current_code and current_klines:
                        history[current_code] = current_klines
                    
                    # 开始新股票
                    current_code = code
                    current_klines = []
                
                current_klines.append({
                    'date': row[1],
                    'open': row[2],
                    'close': row[3],
                    'high': row[4],
                    'low': row[5],
                    'volume': row[6],
                    'amount': row[7]
                })
            
            # 保存最后一个股票
            if current_code and current_klines:
                history[current_code] = current_klines
            
            conn.close()
            print(f"[ThreeDimension] 从数据库加载 {len(history)} 只股票历史数据")
            
        except Exception as e:
            print(f"[ThreeDimension] 加载历史数据失败: {e}")
        
        return history
        self.indicators = {}  # 技术指标
        
    def run_full_workflow(self):
        """执行完整的选股工作流"""
        print("=" * 60)
        print("📊 【三维共振选股系统】开始运行")
        print("=" * 60)
        
        start_time = time.time()
        
        # Step 1: 获取数据
        print("\n[Step 1] 获取市场数据...")
        self._fetch_market_data()
        
        # Step 2: 计算技术指标
        print("\n[Step 2] 计算技术指标...")
        self._calculate_indicators()
        
        # Step 3: 第一层 - 大盘趋势与状态
        print("\n[Step 3] 第一层：大盘趋势与状态...")
        market_analysis = self._analyze_market_trend()
        
        # Step 4: 第二层 - 板块强度与资金流向
        print("\n[Step 4] 第二层：板块强度与资金流向...")
        sector_analysis = self._analyze_sector_strength()
        
        # Step 5: 第三层 - 个股相对强度与形态
        print("\n[Step 5] 第三层：个股相对强度与形态...")
        stock_analysis = self._analyze_stock_strength(sector_analysis)
        
        # Step 6: 综合决策
        print("\n[Step 6] 综合决策...")
        final_results = self._generate_final_decision(
            market_analysis, sector_analysis, stock_analysis
        )
        
        elapsed = time.time() - start_time
        print(f"\n✅ 选股完成，耗时: {elapsed:.2f}s")
        
        return final_results
    
    def _fetch_market_data(self):
        """获取市场数据"""
        try:
            from morning_data_source import MorningDataSource
            self.data_source = MorningDataSource()
            self.market_data = self.data_source.get_all_data()
            self.data_source.close()
            
            print(f"[ThreeDimension] A股数据: {len(self.market_data.get('a_stocks', []))}只")
            print(f"[ThreeDimension] ETF期权数据: {len(self.market_data.get('etf_options', []))}只")
        except Exception as e:
            print(f"[ThreeDimension] 数据获取失败: {e}")
            self.market_data = {}
    
    def _calculate_indicators(self):
        """计算技术指标"""
        stocks = self.market_data.get('a_stocks', [])
        etf_options = self.market_data.get('etf_options', [])
        
        # 计算每个股票的指标
        for stock in stocks:
            code = stock.get('code', '')
            price = stock.get('price', 0)
            prev_close = stock.get('prev_close', 0)
            change_pct = stock.get('change_pct', 0)
            volume = stock.get('volume', 0)
            
            # 计算 RPS (简化版：基于当日涨跌幅)
            rps_20 = self._calculate_rps(price, prev_close, change_pct, period=20)
            rps_50 = self._calculate_rps(price, prev_close, change_pct, period=50)
            rps_120 = self._calculate_rps(price, prev_close, change_pct, period=120)
            
            # 计算 DBQR (对比强弱指标)
            dbqr = self._calculate_dbqr(price, prev_close, change_pct)
            
            # 计算 BIAS (乖离率)
            bias = self._calculate_bias(price, prev_close, change_pct)
            
            self.indicators[code] = {
                'rps_20': rps_20,
                'rps_50': rps_50,
                'rps_120': rps_120,
                'dbqr': dbqr,
                'bias': bias,
                'volume': volume,
            }
        
        # 计算 ETF 指标的汇总
        for etf in etf_options:
            symbol = etf.get('symbol', '')
            price = etf.get('price', 0)
            change_pct = etf.get('change_pct', 0)
            
            rps_20 = self._calculate_rps(price, price / (1 + change_pct / 100), change_pct, period=20)
            
            self.indicators[symbol] = {
                'rps_20': rps_20,
                'type': 'etf',
            }
    
    def calculate_rps(self, code: str, period: int = 20) -> float:
        """
        计算相对强度指标(RPS)
        
        Args:
            code: 股票代码
            period: 计算周期(20/50/120)
            
        Returns:
            float: RPS值(0-100)，越高越强
        """
        import sqlite3
        
        # 优先从数据库读取
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 获取该股票最近period+1天的收盘价
            cursor.execute('''
                SELECT close, date 
                FROM stock_klines 
                WHERE code = ? 
                ORDER BY date DESC 
                LIMIT ?
            ''', (code, period + 1))
            
            rows = cursor.fetchall()
            conn.close()
            
            if len(rows) < period + 1:
                return 0
            
            # 计算该股票的涨跌幅
            current_close = rows[0][0]
            previous_close = rows[-1][0]
            
            if previous_close == 0:
                return 0
            
            stock_change_pct = ((current_close - previous_close) / previous_close) * 100
            
            # 获取所有股票的同期涨跌幅，计算排名
            cursor.execute('''
                SELECT code, close, date
                FROM stock_klines
                WHERE date = (SELECT MAX(date) FROM stock_klines)
            ''')
            latest_dates = cursor.fetchall()
            
            if not latest_dates:
                return 0
            
            latest_date = latest_dates[0][2]
            
            # 获取所有股票在period周期前的收盘价
            cursor.execute('''
                SELECT sk.code, sk.close as latest_close, prev.close as previous_close
                FROM stock_klines sk
                LEFT JOIN stock_klines prev ON sk.code = prev.code AND prev.date = (
                    SELECT date FROM stock_klines 
                    WHERE code = sk.code 
                    ORDER BY date DESC 
                    LIMIT 1 OFFSET ?
                )
                WHERE sk.date = ?
                AND sk.code IN (
                    SELECT DISTINCT code FROM stock_klines
                )
            ''', (period, latest_date))
            
            all_stocks = cursor.fetchall()
            conn.close()
            
            # 计算所有股票的涨跌幅
            changes = []
            for stock_code, latest, previous in all_stocks:
                if previous and previous > 0:
                    change_pct = ((latest - previous) / previous) * 100
                    changes.append(change_pct)
            
            if not changes:
                return 0
            
            # 计算排名
            rank = sum(1 for c in changes if c < stock_change_pct)
            rps = (rank / len(changes)) * 100
            
            return round(rps, 1)
            
        except Exception as e:
            print(f"[ThreeDimension] 计算{code}的RPS({period})失败: {e}")
            return 0
    
    def _calculate_dbqr(self, current_price, base_price, change_pct):
        """
        计算 DBQR (对比强弱指标)
        
        DB = (大盘收盘 - N日前大盘收盘) / N日前大盘收盘
        QB = (个股收盘 - N日前个股收盘) / N日前个股收盘
        """
        if base_price <= 0:
            return 0
        
        # QB: 个股强弱线
        qb = (current_price - base_price) / base_price * 100
        
        # DB: 指数强弱线 (简化为 0，假设大盘无变化)
        db = 0
        
        # DBQR = QB - DB
        dbqr = qb - db
        
        return round(dbqr, 2)
    
    def _calculate_bias(self, current_price, base_price, change_pct):
        """
        计算 BIAS (乖离率)
        
        BIAS = (收盘价 - N日移动平均价) / N日移动平均价 * 100
        """
        if base_price <= 0:
            return 0
        
        # 简化处理：使用 prev_close 作为参考
        bias = (current_price - base_price) / base_price * 100
        
        return round(bias, 2)
    
    def _analyze_market_trend(self):
        """
        第一层：大盘趋势与状态
        
        分析内容：
        - 趋势确认：200日均线/趋势线
        - 状态划分：可操作区/警戒区/休息区
        - 仓位指导：总仓位上限
        """
        analysis = {
            'status': 'unknown',
            'position_limit': 0,
            'trend': 'unknown',
            'details': [],
        }
        
        # 简化处理：基于 ETF 表现判断大盘状态
        etf_options = self.market_data.get('etf_options', [])
        if not etf_options:
            analysis['details'].append("⚠️ 暂无 ETF 数据，无法判断大盘趋势")
            return analysis
        
        # 计算 ETF 平均涨跌幅
        total_pct = sum(etf.get('change_pct', 0) for etf in etf_options)
        avg_pct = total_pct / len(etf_options) if etf_options else 0
        
        analysis['avg_etf_change'] = round(avg_pct, 2)
        
        if avg_pct > 1:
            analysis['status'] = '可操作区'
            analysis['position_limit'] = 80
            analysis['trend'] = '强势上涨'
            analysis['details'].append(f"🟢 大盘强势上涨，ETF 平均涨幅: {avg_pct:.2f}%")
            analysis['details'].append("💡 建议仓位：60%-80%")
        elif avg_pct > 0:
            analysis['status'] = '可操作区'
            analysis['position_limit'] = 60
            analysis['trend'] = '震荡上行'
            analysis['details'].append(f"🟡 大盘震荡上行，ETF 平均涨幅: {avg_pct:.2f}%")
            analysis['details'].append("💡 建议仓位：40%-60%")
        elif avg_pct > -1:
            analysis['status'] = '警戒区'
            analysis['position_limit'] = 30
            analysis['trend'] = '震荡下行'
            analysis['details'].append(f"🟠 大盘震荡下行，ETF 平均涨幅: {avg_pct:.2f}%")
            analysis['details'].append("💡 建议仓位：10%-30%")
        else:
            analysis['status'] = '休息区'
            analysis['position_limit'] = 10
            analysis['trend'] = '弱势下跌'
            analysis['details'].append(f"🔴 大盘弱势下跌，ETF 平均涨幅: {avg_pct:.2f}%")
            analysis['details'].append("💡 建议仓位：0%-10%，观望为主")
        
        return analysis
    
    def _analyze_sector_strength(self):
        """
        第二层：板块强度与资金流向
        
        分析内容：
        - RPS 板块排序：20 日涨幅前 10%-15%
        - 资金流向分析：主力净流入/流出
        - 板块趋势：突破/回调/破位
        """
        analysis = {
            'strong_sectors': [],
            'weak_sectors': [],
            'details': [],
        }
        
        # 简化处理：基于 ETF 表现分析板块强度
        etf_options = self.market_data.get('etf_options', [])
        if not etf_options:
            analysis['details'].append("⚠️ 暂无 ETF 数据，无法分析板块强度")
            return analysis
        
        # 按涨跌幅排序
        sorted_etfs = sorted(etf_options, key=lambda x: x.get('change_pct', 0), reverse=True)
        
        # 识别强势板块（涨幅前 15%）
        strong_count = max(1, int(len(sorted_etfs) * 0.15))
        for etf in sorted_etfs[:strong_count]:
            name = etf.get('name', '')
            pct = etf.get('change_pct', 0)
            analysis['strong_sectors'].append({
                'name': name,
                'rps_20': self.indicators.get(etf.get('symbol', ''), {}).get('rps_20', 0),
                'change_pct': pct,
                'volume': etf.get('volume', 0),
                'amount_yi': etf.get('amount_yi', 0),
            })
        
        # 识别弱势板块（跌幅后 15%）
        weak_count = max(1, int(len(sorted_etfs) * 0.15))
        for etf in sorted_etfs[-weak_count:]:
            name = etf.get('name', '')
            pct = etf.get('change_pct', 0)
            analysis['weak_sectors'].append({
                'name': name,
                'rps_20': self.indicators.get(etf.get('symbol', ''), {}).get('rps_20', 0),
                'change_pct': pct,
                'volume': etf.get('volume', 0),
                'amount_yi': etf.get('amount_yi', 0),
            })
        
        # 生成分析详情
        if analysis['strong_sectors']:
            analysis['details'].append(f"🔥 强势板块 ({len(analysis['strong_sectors'])}个):")
            for sector in analysis['strong_sectors'][:5]:
                analysis['details'].append(
                    f"  - {sector['name']}: RPS={sector['rps_20']:.1f}, "
                    f"涨幅={sector['change_pct']:.2f}%"
                )
        
        if analysis['weak_sectors']:
            analysis['details'].append(f"⚠️ 弱势板块 ({len(analysis['weak_sectors'])}个):")
            for sector in analysis['weak_sectors'][:5]:
                analysis['details'].append(
                    f"  - {sector['name']}: RPS={sector['rps_20']:.1f}, "
                    f"跌幅={sector['change_pct']:.2f}%"
                )
        
        return analysis
    
    def _analyze_stock_strength(self, sector_analysis):
        """
        第三层：个股相对强度与形态
        
        分析内容：
        - 多周期 RPS 共振：50 日/120 日/20 日
        - 量价配合：突破日量能放大
        - 位置与形态：底部突破/高位风险
        """
        analysis = {
            'strong_stocks': [],
            'weak_stocks': [],
            'watch_list': [],
            'details': [],
        }
        
        stocks = self.market_data.get('a_stocks', [])
        if not stocks:
            analysis['details'].append("⚠️ 暂无 A 股数据")
            return analysis
        
        # 筛选强势股（RPS 共振 + 量价配合）
        for stock in stocks:
            code = stock.get('code', '')
            name = stock.get('name', '')
            price = stock.get('price', 0)
            change_pct = stock.get('change_pct', 0)
            volume = stock.get('volume', 0)
            indicators = self.indicators.get(code, {})
            
            rps_20 = indicators.get('rps_20', 0)
            rps_50 = indicators.get('rps_50', 0)
            rps_120 = indicators.get('rps_120', 0)
            dbqr = indicators.get('dbqr', 0)
            bias = indicators.get('bias', 0)
            
            # 检查多周期 RPS 共振
            is_resonance = (rps_20 > 70 and rps_50 > 65 and rps_120 > 60)
            
            # 检查 DBQR 金叉
            is_golden_cross = dbqr > 0
            
            # 检查量价配合（简化处理）
            is_volume_support = volume > 1000000  # 成交量大于 100 万股
            
            # 综合评分
            score = 0
            if is_resonance:
                score += 3
            if is_golden_cross:
                score += 2
            if is_volume_support:
                score += 1
            if change_pct > 3:
                score += 1
            elif change_pct < -3:
                score -= 1
            
            stock_info = {
                'code': code,
                'name': name,
                'price': price,
                'change_pct': change_pct,
                'volume': volume,
                'rps_20': rps_20,
                'rps_50': rps_50,
                'rps_120': rps_120,
                'dbqr': dbqr,
                'bias': bias,
                'score': score,
            }
            
            if score >= 5:
                analysis['strong_stocks'].append(stock_info)
            elif score >= 3:
                analysis['watch_list'].append(stock_info)
            else:
                analysis['weak_stocks'].append(stock_info)
        
        # 按评分排序
        analysis['strong_stocks'].sort(key=lambda x: x['score'], reverse=True)
        analysis['watch_list'].sort(key=lambda x: x['score'], reverse=True)
        analysis['weak_stocks'].sort(key=lambda x: x['score'])
        
        # 生成分析详情
        if analysis['strong_stocks']:
            analysis['details'].append(f"🎯 强势股 ({len(analysis['strong_stocks'])}只):")
            for stock in analysis['strong_stocks'][:10]:
                analysis['details'].append(
                    f"  - {stock['code']} {stock['name']}: "
                    f"价格={stock['price']:.2f}, "
                    f"涨幅={stock['change_pct']:+.2f}%, "
                    f"RPS(20/50/120)={stock['rps_20']:.1f}/{stock['rps_50']:.1f}/{stock['rps_120']:.1f}, "
                    f"DBQR={stock['dbqr']:.2f}, "
                    f"评分={stock['score']}"
                )
        
        if analysis['watch_list']:
            analysis['details'].append(f"👀 关注列表 ({len(analysis['watch_list'])}只):")
            for stock in analysis['watch_list'][:5]:
                analysis['details'].append(
                    f"  - {stock['code']} {stock['name']}: "
                    f"价格={stock['price']:.2f}, "
                    f"涨幅={stock['change_pct']:+.2f}%, "
                    f"评分={stock['score']}"
                )
        
        return analysis
    
    def _generate_final_decision(self, market_analysis, sector_analysis, stock_analysis):
        """
        综合决策：结合三层分析结果，给出最终选股建议
        """
        decision = {
            'market_status': market_analysis.get('status', 'unknown'),
            'position_suggestion': f"{market_analysis.get('position_limit', 0)}%",
            'strong_sectors': sector_analysis.get('strong_sectors', []),
            'strong_stocks': stock_analysis.get('strong_stocks', []),
            'watch_list': stock_analysis.get('watch_list', []),
            'recommendations': [],
            'risk_warnings': [],
        }
        
        # 生成推荐建议
        if market_analysis.get('status') == '可操作区':
            if stock_analysis.get('strong_stocks'):
                decision['recommendations'].append(
                    f"✅ 建议买入 {len(stock_analysis['strong_stocks'])} 只强势股"
                )
                for stock in stock_analysis['strong_stocks'][:3]:
                    decision['recommendations'].append(
                        f"  - {stock['code']} {stock['name']}: "
                        f"入场条件: 突破{stock['price'] * 1.03:.2f}元, "
                        f"止损:{stock['price'] * 0.97:.2f}元, "
                        f"目标:{stock['price'] * 1.05:.2f}元"
                    )
        
        if market_analysis.get('status') == '警戒区':
            decision['risk_warnings'].append(
                "⚠️ 市场处于警戒区，建议控制仓位在 30% 以下"
            )
            decision['risk_warnings'].append(
                "💡 重点关注强势板块中的低位启动股"
            )
        
        if market_analysis.get('status') == '休息区':
            decision['risk_warnings'].append(
                "🛑 市场处于休息区，建议空仓或极低仓位观望"
            )
            decision['risk_warnings'].append(
                "💡 等待大盘企稳信号出现后再考虑介入"
            )
        
        # 添加风险提示
        if stock_analysis.get('strong_stocks'):
            decision['risk_warnings'].append(
                "⚠️ 注意：RPS 极高（>95）且股价连续大涨后，警惕获利盘兑现"
            )
            decision['risk_warnings'].append(
                "💡 严格执行止损纪律，建议亏损达 7%-8% 时离场"
            )
        
        return decision


if __name__ == '__main__':
    # 测试选股系统
    print("=" * 60)
    print("📊 三维共振选股系统测试")
    print("=" * 60)
    
    selector = ThreeDimensionSelector()
    results = selector.run_full_workflow()
    
    # 打印结果
    print("\n" + "=" * 60)
    print("📈 【选股结果】")
    print("=" * 60)
    
    print(f"\n📊 市场状态: {results['market_status']}")
    print(f"💰 建议仓位: {results['position_suggestion']}")
    
    print(f"\n🔥 强势板块:")
    for sector in results['strong_sectors'][:5]:
        print(f"  - {sector['name']}: RPS={sector['rps_20']:.1f}, 涨幅={sector['change_pct']:.2f}%")
    
    print(f"\n🎯 强势股:")
    for stock in results['strong_stocks'][:10]:
        print(f"  - {stock['code']} {stock['name']}: "
              f"价格={stock['price']:.2f}, "
              f"涨幅={stock['change_pct']:+.2f}%, "
              f"RPS(20/50/120)={stock['rps_20']:.1f}/{stock['rps_50']:.1f}/{stock['rps_120']:.1f}, "
              f"评分={stock['score']}")
    
    print(f"\n👀 关注列表:")
    for stock in results['watch_list'][:5]:
        print(f"  - {stock['code']} {stock['name']}: "
              f"价格={stock['price']:.2f}, "
              f"涨幅={stock['change_pct']:+.2f}%, "
              f"评分={stock['score']}")
    
    print(f"\n💡 推荐建议:")
    for rec in results['recommendations']:
        print(f"  {rec}")
    
    print(f"\n⚠️ 风险提示:")
    for warning in results['risk_warnings']:
        print(f"  {warning}")
    
    # 保存结果
    output_file = f'projects/three_dimension_selection_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2, default=str)
    print(f"\n💾 选股结果已保存到: {output_file}")
    
    print("\n✅ 选股系统测试完成")
