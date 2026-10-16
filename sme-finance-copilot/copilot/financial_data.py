"""Shared canonical projection; existing financial formulas are retained."""
import copy,hashlib,json,time
from datetime import date,datetime,timedelta,timezone
from decimal import Decimal
from copilot import config
from copilot.canonical_transactions import normalize,OFFSETS,zone
from copilot.reliability import EvidenceError

class FinancialData:
    def __init__(self,copilot):
        self.c=copilot;self.base=copy.deepcopy(copilot.merchants);self.journal=None;self.ephemeral={}
    def attach(self,journal):
        self.journal=journal
        self.restore_payments()
    def rows(self,mid):
        records=self.journal.read()[0] if self.journal else self.ephemeral
        return [copy.deepcopy(r) for r in records.values() if r['merchant_id']==mid and r.get('source')!='simulated_payment']
    def as_of(self,mid):
        days=[date.fromisoformat(r['business_date']) for r in self.rows(mid)]
        return max([self.c.as_of,*days])
    def version(self,mid):
        return hashlib.sha256(json.dumps([self.rows(mid),self.base[mid].currency,config.RBF,config.CASHFLOW],sort_keys=True,default=str).encode()).hexdigest()
    def project(self,mid):
        m=copy.deepcopy(self.base[mid])
        for row in self.rows(mid):
            self.validate(row,m)
            if row['status']!='completed':continue
            amount=Decimal(row['amount']);kind=row['transaction_type']
            target=m.expenses if kind=='expense' else m.transactions
            target.append({'id':row['transaction_id'],'date':row['business_date'],'amount':float(abs(amount) if kind=='expense' else amount),
                           'channel':row['payment_method'],'category':row.get('category','other'),'count':1,'source':row['source']})
        return m
    def validate(self,row,m):
        try:
            number=Decimal(row['amount'])
            if row['merchant_id']!=m.merchant_id or row['currency']!=m.currency:raise ValueError()
            if not number.is_finite() or number!=number.quantize(Decimal('.01')):raise ValueError()
            date.fromisoformat(row['business_date'])
            if row['payment_method'] not in config.CHANNELS or row['transaction_type'] not in ('sale','expense','refund','reversal'):raise ValueError()
            if row['status'] not in ('completed','pending','failed','voided'):raise ValueError()
        except (ValueError,KeyError,ArithmeticError):raise EvidenceError('Invalid canonical financial record') from None
    def aggregate(self,mid,start=None,end=None):
        end=date.fromisoformat(end) if isinstance(end,str) else end or self.as_of(mid)
        start=date.fromisoformat(start) if isinstance(start,str) else start or end-timedelta(days=89)
        if start>end:raise EvidenceError('Reporting period starts after its end')
        currency=self.base[mid].currency
        gross_known=True;gross_total=Decimal(0)
        totals={'positive_sales':Decimal(0),'refunds':Decimal(0),'net_sales':Decimal(0),'expenses':Decimal(0),'completed_transactions':0,'pending_transactions':0,'failed_transactions':0,'voided_transactions':0}
        provenance={};methods={};count=0
        def add(kind,amount,channel,source,n=1):
            nonlocal count
            count+=1;totals['completed_transactions']+=n;provenance[source]=provenance.get(source,0)+n
            if kind=='expense':totals['expenses']+=abs(amount)
            else:
                totals['net_sales']+=amount
                if amount<0:totals['refunds']+=abs(amount)
                else:totals['positive_sales']+=amount
                methods[channel]=methods.get(channel,Decimal(0))+amount
        for row in self.base[mid].transactions:
            if start<=date.fromisoformat(row['date'])<=end:
                gross_known=False
                add('sale',Decimal(str(row['amount'])),row['channel'],'synthetic_seed',row.get('count',1))
        for row in self.base[mid].expenses:
            if start<=date.fromisoformat(row['date'])<=end:add('expense',Decimal(str(row['amount'])),row.get('channel','cash'),'synthetic_seed')
        for row in self.rows(mid):
            self.validate(row,self.base[mid])
            if not start<=date.fromisoformat(row['business_date'])<=end:continue
            if row['status']!='completed':
                totals[row['status']+'_transactions']+=1;continue
            source='simulated_payment' if row['source']=='simulated_payment' else 'manual' if row['source'] in ('manual','legacy_manual') else 'historical_pos'
            if row['transaction_type']=='sale':
                if row.get('gross_amount') is None:gross_known=False
                else:gross_total+=Decimal(row['gross_amount'])
            add(row['transaction_type'],Decimal(row['amount']),row['payment_method'],source)
        return {'merchant_id':mid,'currency':currency,'period_start':start.isoformat(),'period_end':end.isoformat(),
                **{k:format(v.quantize(Decimal('.01')),'.2f') if isinstance(v,Decimal) else v for k,v in totals.items()},
                'gross_sales':format(gross_total,'.2f') if gross_known else None,'net_income':format((totals['net_sales']-totals['expenses']).quantize(Decimal('.01')),'.2f'),
                'payment_methods':{k:format(v.quantize(Decimal('.01')),'.2f') for k,v in methods.items()},'provenance':provenance,
                'record_count':count,'data_version':self.version(mid),'as_of':datetime.now(timezone.utc).isoformat(),
                'limitations':(['Gross sales are unavailable where sources provide net amounts without gross components.'] if not gross_known else [])+([__import__('copilot.currency_policy',fromlist=['legacy_note']).legacy_note(currency)] if currency!='CNY' else [])+['Recorded revenue is not available cash.','Synthetic seed data is demonstration evidence, not bank settlement evidence. Digital Payments Simulator activity is excluded.']}
    def dashboard(self,mid,start=None,end=None,granularity='monthly'):
        from copilot.modules.dashboard import build_dashboard
        result=build_dashboard(self.project(mid),self.as_of(mid),date.fromisoformat(start) if start else None,date.fromisoformat(end) if end else None,granularity)
        metrics=self.aggregate(mid,start,end)
        result['channel_performance']=self.channel_performance(mid,start,end)
        result['financial_metrics']=metrics
        result['mix']['gross_revenue']=float(metrics['net_sales']) # compatibility label; UI now calls this recorded net sales
        result['expenses']=float(metrics['expenses']);result['net_income']=float(Decimal(metrics['net_sales'])-Decimal(metrics['expenses']))
        result['provenance']=metrics['provenance'];result['data_freshness']=metrics['as_of']
        return result
    def channel_performance(self,mid,start=None,end=None):
        """Recorded sales/payment counts and net values; simulator excluded by projection."""
        metrics=self.aggregate(mid,start,end)
        start=metrics['period_start'];end=metrics['period_end']
        counts={}
        for row in self.project(mid).transactions:
            if start<=row['date']<=end:
                channel=row['channel'];counts[channel]=counts.get(channel,0)+row.get('count',1)
        amounts={k:Decimal(v) for k,v in metrics['payment_methods'].items()}
        total=sum(counts.values());net=Decimal(metrics['net_sales'])
        reconciled=sum(amounts.values(),Decimal(0))==net and set(counts)==set(amounts)
        reason=None
        if not reconciled:reason='Channel values cannot be reconciled with recorded net sales.'
        elif total<=0:reason='No eligible recorded sales/payment transactions in this period.'
        elif net<=0:reason='Revenue contribution is unavailable because total recorded net sales are zero or negative.'
        elif any(v<0 for v in amounts.values()):reason='Revenue contribution is unavailable because a channel has negative recorded net sales.'
        share_ok=reconciled and total>0 and net>0 and all(v>=0 for v in amounts.values())
        return {'merchant_id':mid,'currency':metrics['currency'],'period_start':start,'period_end':end,
                'available':reconciled and total>0,'revenue_available':share_ok,'message':reason,
                'total_transactions':total,'net_sales':str(net),'channels':[
                    {'channel':k,'label':config.CHANNELS[k]['label'],'transactions':counts[k],
                     'net_sales':str(amounts.get(k,Decimal(0))),
                     'count_percent':float(Decimal(counts[k])*100/total) if reconciled and total>0 else None,
                     'revenue_percent':float(amounts[k]*100/net) if share_ok else None} for k in counts],
                'note':'Completed recorded sales, refunds and reversals; expenses and Digital Payments Simulator excluded. Synthetic seed activity remains demo evidence. Percentages may differ slightly due to display rounding.'}

    def record_payment(self,p):
        # Simulator state has its own SQLite tables; never append a financial row.
        self.persist_payment(p)
    def record_refund(self,p,amount,reference):
        # Final simulator state/refund idempotency is persisted by its event callback.
        # No canonical ledger, cash-flow or financial report writes are permitted.
        return None

    def persist_payment(self,p):
        auth=self.c.identity_store
        if not auth:return
        with auth.db() as db:
            db.execute('INSERT INTO simulated_payment_state(reference,merchant_id,state_json,updated_at) VALUES(?,?,?,?) ON CONFLICT(reference) DO UPDATE SET state_json=excluded.state_json,updated_at=excluded.updated_at',(p.ref,p.merchant_id,json.dumps(p.public()),self.c.clock()))
            db.execute('INSERT INTO simulated_wallet_state(merchant_id,amount) VALUES(?,?) ON CONFLICT(merchant_id) DO UPDATE SET amount=excluded.amount',(p.merchant_id,format(Decimal(str(self.c.payments.wallets.get(p.merchant_id,0))),'.2f')))
            for key,result in self.c.payments.refunds.items():
                if result['ref'] in self.c.payments.payments and self.c.payments.payments[result['ref']].merchant_id==p.merchant_id:
                    db.execute('INSERT OR IGNORE INTO simulated_refund_state VALUES(?,?,?)',(key,p.merchant_id,json.dumps(result)))

    def restore_payments(self):
        auth=self.c.identity_store
        if not auth:return
        from copilot.modules.payments import Payment
        with auth.db() as db:
            rows=db.execute('SELECT * FROM simulated_payment_state').fetchall()
            wallets=db.execute('SELECT * FROM simulated_wallet_state').fetchall()
            refunds=db.execute('SELECT * FROM simulated_refund_state').fetchall()
        for row in rows:
            data=json.loads(row['state_json'])
            if row['merchant_id'] not in self.c.merchants or data.get('merchant_id')!=row['merchant_id'] or data.get('ref')!=row['reference']:raise EvidenceError('Invalid persisted simulated payment scope')
            if data.get('currency')!=self.c.merchants[row['merchant_id']].currency or not Decimal(str(data.get('amount'))).is_finite():raise EvidenceError('Invalid persisted simulated payment amount/currency')
            self.c.payments.payments[row['reference']]=Payment(**data)
        for row in wallets:
            if row['merchant_id'] in self.c.merchants:
                amount=Decimal(row['amount'])
                if not amount.is_finite():raise EvidenceError('Invalid persisted simulated wallet')
                self.c.payments.wallets[row['merchant_id']]=float(amount)
        for row in refunds:
            if row['merchant_id'] in self.c.merchants:self.c.payments.refunds[row['idempotency_key']]=json.loads(row['result_json'])
        # Historical simulator ledger evidence is retained, never replayed into analytics.

    def existing_refund(self,p,amount,reference):
        records=self.journal.read()[0] if self.journal else self.ephemeral
        row=records.get('REF-'+reference)
        if not row:return None
        if row['merchant_id']!=p.merchant_id or row.get('related_payment_reference')!=p.ref or row['currency']!=p.currency or abs(Decimal(row['amount']))!=Decimal(str(amount)):
            raise EvidenceError('Refund reference is bound to a different exact request')
        return {'ref':p.ref,'refund_reference':reference,'amount':float(abs(Decimal(row['amount']))),'currency':p.currency,'status':'SIMULATED_REFUND','provenance':'simulated_payment'}

    def reconcile_payment_state(self):
        if not self.journal:return
        records=self.journal.read()[0]
        for p in self.c.payments.payments.values():
            sale=records.get('PAY-'+p.ref);changed=False
            if sale and p.status!='PAID':
                self.validate(sale,self.base[p.merchant_id])
                p.status='PAID';p.paid_at=datetime.fromisoformat(sale['transaction_date'].replace('Z','+00:00')).timestamp();p.paid_channel=sale['payment_method'];p.net_settled=float(Decimal(sale.get('settlement_amount') or '0'))
                self.c.payments.wallets[p.merchant_id]=round(self.c.payments.wallets.get(p.merchant_id,0)+p.net_settled,2);changed=True
            refunds=[r for r in records.values() if r.get('related_payment_reference')==p.ref and r['merchant_id']==p.merchant_id]
            refunded=sum((abs(Decimal(r['amount'])) for r in refunds),Decimal(0))
            if refunded>Decimal(str(p.amount)) or refunded<Decimal(str(p.refunded_amount)):raise EvidenceError('Persisted refund state disagrees with canonical records')
            if refunded>Decimal(str(p.refunded_amount)):
                missing=refunded-Decimal(str(p.refunded_amount));known=Decimal(str(p.refunded_amount));delta=Decimal(0)
                for row in sorted(refunds,key=lambda r:r.get('created_at','')):
                    amount=abs(Decimal(row['amount']))
                    if known>=amount:known-=amount;continue
                    if row.get('wallet_delta') is None:raise EvidenceError('Interrupted refund lacks its exact wallet effect; review required')
                    delta+=Decimal(row['wallet_delta'])
                self.c.payments.wallets[p.merchant_id]=float(Decimal(str(self.c.payments.wallets.get(p.merchant_id,0)))+delta)
                p.refunded_amount=float(refunded);changed=True
            if changed:self.persist_payment(p)
