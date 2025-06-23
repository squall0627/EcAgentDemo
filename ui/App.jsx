// 📁 File: App.jsx
import React, { useState, useEffect } from "react";
import axios from "axios";

export default function App() {
    const [messages, setMessages] = useState([]);
    const [input, setInput] = useState("");
    const [products, setProducts] = useState([]);
    const [selected, setSelected] = useState([]);
    const [page, setPage] = useState(1);
    const [filters, setFilters] = useState({ category: "", lang: "zh" });
    const [errors, setErrors] = useState([]);

    const fetchProducts = async () => {
        const res = await axios.get("/products", {
            params: {
                status: "unpublished",
                page,
                category: filters.category,
                lang: filters.lang,
            },
        });
        setProducts(res.data);
    };

    const sendMessage = async () => {
        const res = await axios.post("/agent/chat", {
            message: input,
            selected_product_ids: selected,
        });
        setMessages([...messages, { role: "user", content: input }, res.data.reply]);
        setInput("");

        if (res.data.products) {
            setProducts(res.data.products);
        }
        if (res.data.errors) {
            setErrors(res.data.errors);
        }
    };

    const toggleSelect = (id) => {
        setSelected((prev) =>
            prev.includes(id) ? prev.filter((pid) => pid !== id) : [...prev, id]
        );
    };

    const handlePageChange = (offset) => {
        setPage((prev) => Math.max(1, prev + offset));
    };

    useEffect(() => {
        fetchProducts();
    }, [page, filters]);

    return (
        <div className="p-4 max-w-5xl mx-auto">
            <h1 className="text-2xl font-bold mb-4">AI EC Back Office Agent</h1>

            <div className="border p-4 rounded bg-gray-100 mb-4 h-64 overflow-y-auto">
                {messages.map((m, i) => (
                    <div key={i} className={m.role === "user" ? "text-right" : "text-left"}>
                        <p><strong>{m.role === "user" ? "👤" : "🤖"}</strong> {m.content}</p>
                    </div>
                ))}
            </div>

            <div className="flex gap-2 mb-4">
                <input
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    className="border rounded px-2 py-1 flex-grow"
                    placeholder="请输入指令，如 显示未上架商品"
                />
                <button onClick={sendMessage} className="bg-blue-500 text-white px-4 rounded">
                    发送
                </button>
            </div>

            <div className="flex gap-4 items-center mb-4">
                <label>
                    分类：
                    <input
                        type="text"
                        value={filters.category}
                        onChange={(e) => setFilters({ ...filters, category: e.target.value })}
                        className="border px-2 py-1 rounded ml-2"
                    />
                </label>
                <label>
                    语言：
                    <select
                        value={filters.lang}
                        onChange={(e) => setFilters({ ...filters, lang: e.target.value })}
                        className="border px-2 py-1 rounded ml-2"
                    >
                        <option value="zh">中文</option>
                        <option value="en">English</option>
                        <option value="jp">日本語</option>
                    </select>
                </label>
            </div>

            {errors.length > 0 && (
                <div className="bg-yellow-100 border-l-4 border-yellow-500 text-yellow-700 p-4 mb-4">
                    <p className="font-bold">⚠️ 上架前检查失败：</p>
                    <ul className="list-disc pl-5">
                        {errors.map((e, i) => (
                            <li key={i}>{e}</li>
                        ))}
                    </ul>
                    <p className="mt-2">你可以通过自然语言继续修复，例如：“为商品A设置分类为‘母婴’”。</p>
                </div>
            )}

            {products.length > 0 && (
                <div className="overflow-x-auto rounded-lg shadow">
                    <table className="w-full text-sm text-left border">
                        <thead className="bg-gray-50">
                        <tr>
                            <th className="p-2">选择</th>
                            <th className="p-2">商品名</th>
                            <th className="p-2">分类</th>
                            <th className="p-2">状态</th>
                            <th className="p-2">库存</th>
                        </tr>
                        </thead>
                        <tbody>
                        {products.map((p) => (
                            <tr key={p.id} className="border-t bg-white hover:bg-gray-50">
                                <td className="p-2">
                                    <input
                                        type="checkbox"
                                        checked={selected.includes(p.id)}
                                        onChange={() => toggleSelect(p.id)}
                                    />
                                </td>
                                <td className="p-2">{p.name}</td>
                                <td className="p-2">{p.category || <span className="text-red-500">未分类</span>}</td>
                                <td className="p-2">{p.status}</td>
                                <td className="p-2">{p.stock === 0 ? <span className="text-red-500">无库存</span> : p.stock}</td>
                            </tr>
                        ))}
                        </tbody>
                    </table>
                    <div className="flex justify-between items-center mt-2">
                        <button onClick={() => handlePageChange(-1)} className="px-3 py-1 bg-gray-200 rounded">
                            上一页
                        </button>
                        <span>第 {page} 页</span>
                        <button onClick={() => handlePageChange(1)} className="px-3 py-1 bg-gray-200 rounded">
                            下一页
                        </button>
                    </div>
                </div>
            )}
        </div>
    );
}