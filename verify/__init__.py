#coding: utf-8
# discord stuff
# for type hint
from typing import * # pyright: ignore

import discord, asyncio, re
from discord.ext import commands, tasks
from discord.abc import *

from main import GDSCCommBot, SERVER_ID, SERVER_VERIFY_CHANNEL, VERIFIED_ROLE, STUPTIT_ROLE, SERVER_WELCOME_CHANNEL, DB_HOST, DB_NAME, DB_PASSWORD, DB_PORT, DB_USER

from .otp import OTP

import psycopg2 as psql

from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.header import Header

# view in verify channel
class GlobalVerifyMsgView(discord.ui.View):
    def __init__(self, verifyCallback: Callable) -> None:
        super().__init__(timeout=None)
        self.verifyCallback: Callable = verifyCallback

    @discord.ui.button(label="Xác minh danh tính", style=discord.ButtonStyle.green)
    async def buttonCallback( self, interaction: discord.Interaction, button ) -> None:
        member: discord.Member = interaction.guild.get_member(interaction.user.id)
        await interaction.response.send_message("Tin nhắn xác minh danh tính đã được gửi tới bạn !", ephemeral=True)
        await self.verifyCallback(member)

class DoesntReceiveOTPView(discord.ui.View):
    def __init__(self, sendOTPCallback: Callable, userEmail: str, currentOTP: str) -> None:
        super().__init__(timeout=None)

        self.sendOTPCallback: Callable = sendOTPCallback
        self.userEmail: str = userEmail
        self.currentOTP: str = currentOTP

    @discord.ui.button(label="Tôi chưa nhận được mã", style=discord.ButtonStyle.red)
    async def buttonCallback( self, interaction: discord.Interaction, button: discord.Button ) -> None:
        button.disabled = True
        await interaction.response.send_message(f"Mã OTP đã được gửi lại vào **{self.userEmail}** !")
        self.sendOTPCallback(self.userEmail, self.currentOTP)

# verify cog
class Verify( commands.Cog ):
    def __init__( self, bot: commands.Bot ):
        self.bot: GDSCCommBot = bot

        self.createGlobalVerifyMessage.start()
        self.restart_psql_connect.start()

    # ping command first basical command for discord bot
    @commands.command( name="ping", description="Lấy thời gian phàn hồi của bot", brief="Lấy thời gian phản hồi của bot" )
    async def ping( self, ctx: commands.Context[Any] ) -> None:
        # calculate ping as milliseconds
        packetPing: int = int(self.bot.latency * 1000)
        await ctx.send(':ping_pong: **Pong! {0:,}ms**'.format(packetPing))

    @tasks.loop(hours=12)
    async def restart_psql_connect(self):
        # setup postgresql
        self.bot.conn = psql.connect(
            database=DB_NAME,
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASSWORD,
            port=DB_PORT
        )
        # postgre cursor
        self.bot.sql = self.bot.conn.cursor()

    @tasks.loop(count=1)
    async def createGlobalVerifyMessage( self ) -> None:
        verifyChannel: discord.TextChannel = self.bot.get_guild(SERVER_ID).get_channel(SERVER_VERIFY_CHANNEL)
        await verifyChannel.send("**Dành cho những bạn chưa xác minh danh tính**\n\nCó một số bạn quên chưa điền mail trong quá trình xác nhận hoặc nhập mã OTP sai quá nhiều lần hoặc không nhận được mã OTP trong quá trình xác minh.\n\nCác bạn có thể tiến hành xác minh danh tính bằng cách ấn vào nút dưới đây !", view=GlobalVerifyMsgView(verifyCallback=self.verifyUser))

    #@commands.Cog.listener()
    #async def on_member_join( self, member: discord.Member ) -> None:
    #    await self.verifyUser(member)

    async def verifyUser(self, member: discord.Member) -> None:
        self.bot.sql.execute(f'SELECT discord_id FROM users where discord_id = \'{member.id}\'')
        queryExists = self.bot.sql.fetchone()
        if not queryExists is None:
            await member.send("\n**Bạn đã xác minh danh tính rồi vui lòng quay trở lại :face_with_symbols_over_mouth:**\n")
            return None

        await member.send("**CHÀO MỪNG CÁC HẠ ĐẾN VỚI CỘNG ĐỒNG \"MUỐN MỞ MANG\" CỦA GDSC-PTIT**\n\nCác hạ vui lòng cung cấp **email PTIT** để xác minh danh tính (<name>@stu.ptit.edu.vn). **Lưu ý: admin sẽ nhìn thấy email các hạ dùng xác minh danh tính.**")

        # checking process for each DM
        def check_dm( m: discord.Message ):
            return m.author == member and isinstance(m.channel, discord.DMChannel)

        # server verify channel for mention
        verifyChannel: (GuildChannel | PrivateChannel | discord.Thread | None) = self.bot.get_channel(SERVER_VERIFY_CHANNEL)

        # get user email from user prompt
        while True:
            try:
                userEmailMessage: discord.Message = await self.bot.wait_for('message', check=check_dm, timeout=300.0)
                userEmailMessage.content = userEmailMessage.content.lower()
                if not re.match(r'([A-Za-z0-9]+[.-_])*[A-Za-z0-9]+@[A-Za-z0-9-]+(\.[A-Z|a-z]{2,4})+', userEmailMessage.content):
                    await member.send(f"**Email sử dụng không hợp lệ !**")
                    continue

                # condition for ptit in site the domain name of email
                splitedEmail = userEmailMessage.content.split('@')
                if not "ptit" in splitedEmail[1]:
                    await member.send(f"**Email của bạn sử dụng không phải email của sinh viên PTIT, vui lòng thử lại !!!**")
                    continue

                self.bot.sql.execute(f'SELECT email FROM users WHERE email = \'{userEmailMessage.content}\'')
                emailExists = self.bot.sql.fetchone()
                if not emailExists is None:
                    await member.send("\n**Email này hiện đã có người sử dụng :face_with_symbols_over_mouth:**\n")
                    continue
                else:
                    break
            except asyncio.TimeoutError:
                await member.send(f"**Đã hết 5 phút nhưng các hạ vẫn chưa điền email xác minh danh tính (cũng có thể do email các hạ vừa nhập không đúng định dạng)**.\n Để xác minh danh tính các hạ vui lòng vào discord server của Muốn Mở Mang thực hiện xác minh tại channel {verifyChannel.mention}")
                return None

        # store as another variable for easier reading and using
        userEmail: str = userEmailMessage.content
        userName: str = str('Ẩn sĩ') # user provided name
        userStudentID: str = str('null') # student id if student come from PTIT
        generatorOTP: OTP = OTP(intervalTime=900) # OTP generator with expried time is 15 minutes as 900 seconds
        # store as another variable for easie reading and using
        currentOTPCode: str = generatorOTP.currentOTP

        # if message sent success
        if self.sendOTP(userEmail, currentOTPCode):
            await member.send(f"Mail chứa mã xác nhận đã được gửi tới **{userEmail}**. Vui lòng **check mail trong trang chính hoặc thư mục spam** để nhận được mã OTP có 8 chữ số.", view=DoesntReceiveOTPView(self.sendOTP, userEmail, currentOTPCode))
            failCount = 0
            verifyComplete = False
            countMessage: discord.Message = await member.send(f"Bạn còn **{3 - failCount}** lần thử mã.")
            while failCount < 3:
                await countMessage.edit(content=f"Các hạ còn **{3 - failCount}** cơ hội thử mã.")
                try:
                    userProvideOTP: discord.Message = await self.bot.wait_for('message', check=check_dm, timeout=120.0)
                    userProvideOTP.content = userProvideOTP.content.replace(' ', '')
                    if generatorOTP.verify(userProvideOTP.content):
                        verifyComplete = True
                        break
                    else:
                        failCount += 1
                except asyncio.TimeoutError:
                    await member.send(f"**Đã hết 2 phút nhưng chưa thấy các hạ điền OTP**.\nĐể xác minh danh tính các hạ vui lòng vào discord server của Muốn Mở Mang thực hiện xác minh tại channel {verifyChannel.mention}")
                    return None

            if verifyComplete == False:
                await countMessage.delete()
                await member.send(f"**Danh tính các hạ chưa thể xác minh**.\nĐể xác minh danh tính các hạ vui lòng vào discord server của Muốn Mở Mang thực hiện xác minh tại channel {verifyChannel.mention}")
                return None

            # verify is completed
            # welcome channel
            welcomeChannel: discord.TextChannel = self.bot.get_guild(SERVER_ID).get_channel(SERVER_WELCOME_CHANNEL)
            # when verified complete
            await countMessage.delete()
            await member.send(f"Nhân dạng của tiên sinh đã được xác nhận. **Vui lòng để lại quý danh (đầy đủ Họ và Tên)**:")
            userName = await self.getVerifiedUserName(member)
            splitedUsername = userName.split(' ')
            firstName = splitedUsername[-1].capitalize()
            splitedUsername = splitedUsername[:-1]
            for i in range(0, len(splitedUsername)):
                if len(splitedUsername[i]) > 1:
                    splitedUsername[i] = splitedUsername[i][0].upper()
            userName = firstName + ''.join(splitedUsername)
            # get student id if member using stu.ptit email for verify
            await member.send(f"Mời Quý Sinh viên Hoàng gia \"{userName}\" để lại Mật mã Hoàng gia của riêng bạn (mã sinh viên):")
            userStudentID = await self.getVerifiedUserStudentID(member)
            # regular expression for checking valid student id
            if not re.match(r'[NEB]\d{2}\w{4}\d{3}', userStudentID, re.IGNORECASE):
                await member.send(f"**Rất tiếc !**\nMật mã Hoàng gia không đúng định dạng, nhân dạng không thể xác minh danh tính của quý sinh viên :x:")
                return None


            # create database query for data collect
            insertQuery: str = "INSERT INTO users(discord_id, name, email, student_id) VALUES(%s,%s,%s,%s)"
            self.bot.sql.execute(insertQuery, (member.id, userName, userEmail, userStudentID))
            # already commit the transaction
            self.bot.conn.commit()

            # adding role to user
            serverGuild: discord.Guild = self.bot.get_guild(SERVER_ID) # get GDSC Community Server guild
            verifiedRole: discord.Role = serverGuild.get_role(VERIFIED_ROLE) # verified role id of GDSC Community Server
            stuPTITRole: discord.Role = serverGuild.get_role(STUPTIT_ROLE) # stu ptit role
            # get author as member object
            verifiedMember: discord.Member = member
            try:
                await verifiedMember.add_roles(verifiedRole)
                if "@stu.ptit.edu.vn" in userEmail:
                    await verifiedMember.add_roles(stuPTITRole)
                    await verifiedMember.edit(nick=f"{userName} - {userStudentID}")
                else:
                    await verifiedMember.edit(nick=f"{userName}")
            except discord.Forbidden as e:
                raise e

            await member.send(f"**Xác minh danh tính hoàn tất !**\nMột lần nữa chào mừng bạn đến với cộng đồng Muốn Mở Mang, bạn có thể bắt đầu tại {welcomeChannel.mention} !")
        else:
            await member.send(f"**Xác minh danh tính thất bại do có lỗi xảy ra, vui lòng liên hệ đội ngũ kỹ thuật để báo lỗi và bắt họ fix bug nhé !**")

    # function for get the student id
    async def getVerifiedUserStudentID(self, member: discord.Member) -> str:
        def check_dm( m: discord.Message ):
            if m.author != member or not isinstance(m.channel, discord.DMChannel):
                return False
            return True
        try:
            stuId: discord.Message = await self.bot.wait_for('message', check=check_dm, timeout=120.0)
            return stuId.content.upper()
        except asyncio.TimeoutError:
            await member.send(f"**Đã hết 2 phút nhưng bạn vẫn chưa mã sinh viên của bạn**, nhưng không sao bạn có thể cung cấp nó sau !")

    # function for getting name
    async def getVerifiedUserName(self, member: discord.Member) -> str:
        def check_dm( m: discord.Message ):
            if m.author != member or not isinstance(m.channel, discord.DMChannel):
                return False
            return True
        try:
            name: discord.Message = await self.bot.wait_for('message', check=check_dm, timeout=120.0)
            name = ' '.join(list(map(lambda x: x.capitalize(), name.content.split(' '))))
            return name
        except asyncio.TimeoutError:
            await member.send(f"**Đã hết 2 phút nhưng bạn vẫn chưa điền tên của bạn**, nhưng không sao bạn có thể cung cấp nó sau !")

    # rewrite for reuseable
    def sendOTP(self, userEmail: str, OTP: str) -> bool:

        # create multipart utf-8 message
        message: MIMEMultipart = MIMEMultipart("alternative")
        message["Subject"] = Header("Mã xác nhận danh tính cho Discord cộng đồng Muốn Mở Mang", 'utf-8')

        otpPart_vi: MIMEText = MIMEText("""
            <body>
                <h2>Chào mừng tới với Discord cộng đồng Muốn Mở Mang.</h2>
                <br/><br/>
                Dưới đây là mã xác nhận để bạn có thể xác minh danh tính khi tham gia server.
                Vui lòng gửi đoạn code sau tới MMM Verify Bot để nhận được quyền truy cập. Vui lòng không gửi mã này tới bất kì ai ngoài MMM Verify Bot.
                <br/><br/>
                Mã xác nhận danh tính của bạn: <b>{0} {1}</b>
            </body>
        """.format(OTP[0:4], OTP[4:]), 'html')

        # attach part to message
        message.attach(otpPart_vi)
        # return the result after send email
        return self.bot.email.send(userEmail, message)

# setup function for discord.py load cog
async def setup( bot ):
    await bot.add_cog( Verify(bot) )
