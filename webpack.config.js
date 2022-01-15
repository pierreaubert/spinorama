const fs = require('fs');
const glob = require('glob');
const path = require('path');
const webpack = require('webpack'); 
const { CleanWebpackPlugin } = require("clean-webpack-plugin");
const HtmlWebpackPlugin = require('html-webpack-plugin');
const MiniCssExtractPlugin = require('mini-css-extract-plugin')


const PATHS = {
    html: path.join(__dirname, "./docs"),
    js: path.join(__dirname, "./docs/js"),
    css: path.join(__dirname, "./docs/css"),
    logos: path.join(__dirname, "./docs/logos"),
    pictures: path.join(__dirname, "./docs/pictures"),
    speakers: path.join(__dirname, "./docs/speakers"),
    dist: path.join(__dirname, "./docs/dist"),
};

//  const SPEAKERS_HTML = glob.sync(path.join(PATHS.speakers, '*', '*', 'index*.html')).map( f => f.substring(PATHS.speakers.length+1));
const APP_HTML = glob.sync(path.join(PATHS.html, '*.html')).map( f => f.substring(PATHS.html.length+1));

console.log(APP_HTML);

module.exports = (env, argv) => {
    
    const isEnvDevelopment = argv.mode === "development";
    const isEnvProduction = argv.mode === "production";

    return {
        entry: {
            css: `${PATHS.css}/bulma4spin.scss`,
            misc : `${PATHS.js}/misc.js`,
            onload: `${PATHS.js}/onload.js`,
            search: `${PATHS.js}/search.js`,
            graph: `${PATHS.js}/graph.js`,
            index: {
                import: `${PATHS.js}/index.js`,
                dependOn: ['misc', 'onload', 'search', 'css'],
            },
            eqs: {
                import: `${PATHS.js}/eqs.js`,
                dependOn: ['misc', 'onload', 'search'],
            },
            compare: {
                import: `${PATHS.js}/compare.js`,
                dependOn: ['misc', 'onload'],
            },
            scores: {
                import: `${PATHS.js}/scores.js`,
                dependOn: ['misc', 'onload', 'search'],
            },
        },
        resolve: {
            modules: [
                'node_modules',
                'docs',
            ],
            extensions: [".js", ".flow.js"]
        },
        devtool: isEnvDevelopment ? "eval-cheap-module-source-map" : "source-map",
        output: {
            path: `${PATHS.dist}`,
            filename: 'js/[name].[fullhash].min.js',
        },
        module: {
            rules: [
                {
                    test: /\.scss$/,
                    use: [
                        MiniCssExtractPlugin.loader,
                        {
                            loader: 'css-loader'
                        },
                        {
                            loader: 'sass-loader',
                            options: {
                                sourceMap: true,
                            }
                        }
                    ],
                    exclude: "/node_modules",
                },
                {
                    test: /\.js$/,
                    loader: "babel-loader",
                    exclude: "/node_modules"
                },
                {
                    test: /\.(ico|png|svg)$/,
                    type: "asset/inline",
                },
                {
                    test: /\.html/i,
                    loader: "html-loader",
                },
            ]
        },
        plugins: [
            new MiniCssExtractPlugin({
                filename: 'css/bulma4spin.[hash].min.css'
            }),
            new CleanWebpackPlugin(),
/*
            new HtmlWebpackPlugin({
                template: `${PATHS.html}/speakers/Tannoy Revolution XT6/ASR/asr/On Axis.html`,
                filename: `speakers/Tannoy Revolution XT6/ASR/asr/On Axis.html`,
            }),
*/
            ...APP_HTML.map(
                page => new HtmlWebpackPlugin({
                    template: `${PATHS.html}/${page}`,
                    filename: `${page}`,
                }),
            ),
        ],
        optimization: {
            splitChunks: {
                cacheGroups: {
                    vendor: {
                        name: "vendor",
                        test: /node_modules/,
                        chunks: 'all',
                        enforce: true,
                    },
                },
            },
        },
    }
}
