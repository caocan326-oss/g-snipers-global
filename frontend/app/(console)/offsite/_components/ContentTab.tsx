import { FormEvent } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import type { ContentAsset, FactPack } from "@/lib/api";

type FactForm = {
  name: string;
  legal_name: string;
  brand_names: string;
  website: string;
  product_categories_en: string;
  certifications: string;
  key_specs: string;
  banned_claims: string;
  contact_public: string;
  approved_boilerplate_en: string;
};

type AssetForm = {
  fact_pack_id: string;
  asset_type: string;
  title: string;
  body_md: string;
  locale: string;
  keywords: string;
  entities: string;
};

export function ContentTab({
  factPacks,
  assets,
  approveFactPack,
  reviewAsset,
  approveAsset,
  factForm,
  setFactForm,
  saveFactPack,
  assetForm,
  setAssetForm,
  generateAsset,
  saveAsset,
  copyCustomerPaste,
  copiedAssetId,
}: {
  factPacks: FactPack[];
  assets: ContentAsset[];
  approveFactPack: (id: string) => void;
  reviewAsset: (id: string) => void;
  approveAsset: (id: string) => void;
  factForm: FactForm;
  setFactForm: (form: FactForm) => void;
  saveFactPack: (e: FormEvent) => void;
  assetForm: AssetForm;
  setAssetForm: (form: AssetForm) => void;
  generateAsset: () => void;
  saveAsset: (e: FormEvent) => void;
  copyCustomerPaste: (assetId: string) => void;
  copiedAssetId: string;
}) {
  return (
    <section className="grid gap-5 xl:grid-cols-[1fr_420px]">
      <div className="space-y-4">
        <Card className="rounded-md">
          <CardHeader>
            <CardTitle>客户事实资料</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {factPacks.length ? factPacks.map((fact) => (
              <div key={fact.id} className="rounded-md border border-slate-200 p-4">
                <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
                  <div>
                    <div className="flex flex-wrap items-center gap-2">
                      <h3 className="font-semibold text-slate-950">{fact.name}</h3>
                      <Badge tone={fact.status === "approved" ? "green" : "amber"}>{fact.status === "approved" ? "已批准" : "草稿"}</Badge>
                    </div>
                    <p className="mt-1 text-sm text-slate-500">{fact.legal_name || "未填写公司英文名"} · {fact.website || "未填写官网"}</p>
                    <p className="mt-2 text-sm leading-6 text-slate-600">{fact.approved_boilerplate_en || "还没有标准英文简介。"}</p>
                    <div className="mt-2 grid gap-2 text-xs text-slate-500 md:grid-cols-2">
                      <span>品牌：{fact.brand_names || "未填"}</span>
                      <span>品类：{fact.product_categories_en || "未填"}</span>
                      <span>认证：{fact.certifications || "未填"}</span>
                      <span>禁用语：{fact.banned_claims || "未填"}</span>
                    </div>
                  </div>
                  <Button size="sm" variant="outline" onClick={() => approveFactPack(fact.id)} disabled={fact.status === "approved"}>
                    批准事实包
                  </Button>
                </div>
              </div>
            )) : <p className="text-sm text-slate-500">还没有客户事实资料。先让客户确认公司、品牌、品类、认证和禁用宣传语，再生成对外内容。</p>}
          </CardContent>
        </Card>

        <Card className="rounded-md">
          <CardHeader>
            <CardTitle>对外提交文案</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {assets.length ? assets.map((asset) => (
              <div key={asset.id} className="rounded-md border border-slate-200 p-4">
                <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
                  <div className="min-w-0">
                    <div className="flex flex-wrap items-center gap-2">
                      <h3 className="font-semibold text-slate-950">{asset.title}</h3>
                      <Badge>{asset.asset_type}</Badge>
                      <Badge tone={asset.status === "human_approved" ? "green" : asset.ai_review_status === "fail" ? "red" : "amber"}>
                        {asset.status === "human_approved" ? "人工已批准" : asset.ai_review_status === "fail" ? "初审未过" : asset.status}
                      </Badge>
                    </div>
                    <p className="mt-1 text-xs text-slate-500">{asset.fact_pack_name || "未绑定客户事实资料"} · {asset.locale} · v{asset.version}</p>
                    <p className="mt-3 whitespace-pre-wrap rounded-md bg-slate-50 p-3 text-sm leading-6 text-slate-700">{asset.body_md}</p>
                    {asset.ai_review ? <p className="mt-2 whitespace-pre-wrap text-xs leading-5 text-slate-500">{asset.ai_review}</p> : null}
                  </div>
                  <div className="flex shrink-0 flex-wrap gap-2 lg:w-40">
                    <Button size="sm" variant="outline" onClick={() => copyCustomerPaste(asset.id)} disabled={!(asset.body_md || "").trim()}>
                      {copiedAssetId === asset.id ? "已复制" : "复制给客户"}
                    </Button>
                    <Button size="sm" variant="outline" onClick={() => reviewAsset(asset.id)}>AI 初审</Button>
                    <Button size="sm" onClick={() => approveAsset(asset.id)} disabled={asset.status === "human_approved"}>人工批准</Button>
                  </div>
                </div>
              </div>
            )) : <p className="text-sm text-slate-500">还没有对外提交文案。可以手工粘贴，也可以基于已批准的客户事实资料生成草稿。</p>}
          </CardContent>
        </Card>
      </div>

      <div className="space-y-4">
        <Card className="rounded-md">
          <CardHeader><CardTitle>新增客户事实资料</CardTitle></CardHeader>
          <CardContent>
            <p className="mb-3 text-xs leading-5 text-slate-500">只写已批或官网正文里有的事实。落地页虚数、logo、没写在正文里的认证不要填。</p>
            <form className="space-y-3" onSubmit={saveFactPack}>
              <Input placeholder="事实包名称" value={factForm.name} onChange={(e) => setFactForm({ ...factForm, name: e.target.value })} />
              <Input placeholder="公司英文全称" value={factForm.legal_name} onChange={(e) => setFactForm({ ...factForm, legal_name: e.target.value })} />
              <Input placeholder="品牌名，多个用逗号" value={factForm.brand_names} onChange={(e) => setFactForm({ ...factForm, brand_names: e.target.value })} />
              <Input placeholder="官网" value={factForm.website} onChange={(e) => setFactForm({ ...factForm, website: e.target.value })} />
              <Input placeholder="英文品类词" value={factForm.product_categories_en} onChange={(e) => setFactForm({ ...factForm, product_categories_en: e.target.value })} />
              <Input placeholder="认证/资质，仅填已确认" value={factForm.certifications} onChange={(e) => setFactForm({ ...factForm, certifications: e.target.value })} />
              <Input placeholder="公开参数/规格" value={factForm.key_specs} onChange={(e) => setFactForm({ ...factForm, key_specs: e.target.value })} />
              <Input placeholder="禁用宣传语，例如 world leader" value={factForm.banned_claims} onChange={(e) => setFactForm({ ...factForm, banned_claims: e.target.value })} />
              <Input placeholder="公开联系方式" value={factForm.contact_public} onChange={(e) => setFactForm({ ...factForm, contact_public: e.target.value })} />
              <textarea className="min-h-24 w-full rounded-md border border-slate-200 px-3 py-2 text-sm" placeholder="客户批准的标准英文简介" value={factForm.approved_boilerplate_en} onChange={(e) => setFactForm({ ...factForm, approved_boilerplate_en: e.target.value })} />
              <Button type="submit" className="w-full">保存客户事实资料</Button>
            </form>
          </CardContent>
        </Card>

        <Card className="rounded-md">
          <CardHeader><CardTitle>新增对外提交文案</CardTitle></CardHeader>
          <CardContent>
            <form className="space-y-3" onSubmit={saveAsset}>
              <select className="h-10 w-full rounded-md border border-slate-200 px-3 text-sm" value={assetForm.fact_pack_id} onChange={(e) => setAssetForm({ ...assetForm, fact_pack_id: e.target.value })}>
                <option value="">选择客户事实资料</option>
                {factPacks.map((fact) => <option key={fact.id} value={fact.id}>{fact.name} · {fact.status}</option>)}
              </select>
              <select className="h-10 w-full rounded-md border border-slate-200 px-3 text-sm" value={assetForm.asset_type} onChange={(e) => setAssetForm({ ...assetForm, asset_type: e.target.value })}>
                <option value="company_blurb">公司简介</option>
                <option value="profile_fields">平台档案字段</option>
                <option value="product_spec">产品/规格</option>
                <option value="faq">FAQ</option>
                <option value="listicle_pitch">榜单 Pitch</option>
                <option value="pr_draft">PR 草稿</option>
                <option value="social_snippet">社媒短稿</option>
              </select>
              <Input placeholder="标题" value={assetForm.title} onChange={(e) => setAssetForm({ ...assetForm, title: e.target.value })} required />
              <textarea className="min-h-32 w-full rounded-md border border-slate-200 px-3 py-2 text-sm" placeholder="正文，手工粘贴或点击下方生成草稿" value={assetForm.body_md} onChange={(e) => setAssetForm({ ...assetForm, body_md: e.target.value })} />
              <Input placeholder="关键词" value={assetForm.keywords} onChange={(e) => setAssetForm({ ...assetForm, keywords: e.target.value })} />
              <div className="grid gap-2 sm:grid-cols-2">
                <Button type="button" variant="outline" onClick={generateAsset}>从客户事实资料生成草稿</Button>
                <Button type="submit">保存对外文案</Button>
              </div>
            </form>
          </CardContent>
        </Card>
      </div>
    </section>
  );
}
